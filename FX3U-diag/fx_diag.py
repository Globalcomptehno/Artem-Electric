"""
Диагностика Mitsubishi FX3U (и совместимых клонов) через порт программирования.

ТОЛЬКО ЧТЕНИЕ: скрипт ничего не записывает в контроллер и не трогает программу.

Подключение: кабель USB-SC09-FX / FX-USB-AW (виден в Windows как COMx).
Перед запуском закройте GX Works2 / GX Developer (они занимают COM-порт).

Установка:   pip install pyserial
Запуск:      python fx_diag.py COM3
"""
import sys
import time

try:
    import serial
except ImportError:
    serial = None

STX, ETX, ENQ, ACK, NAK = 0x02, 0x03, 0x05, 0x06, 0x15


def build_read(addr, nbytes):
    """Кадр чтения протокола порта программирования FX: STX '0' AAAA NN ETX SS."""
    body = b"0" + f"{addr:04X}".encode() + f"{nbytes:02X}".encode() + bytes([ETX])
    return bytes([STX]) + body + f"{sum(body) & 0xFF:02X}".encode()


def parse_reply(raw, nbytes):
    """Ответ: STX <данные hex> ETX SS. Возвращает список байтов."""
    if not raw:
        raise IOError("контроллер не ответил (проверьте кабель, COM-порт, питание)")
    if raw[0] == NAK:
        raise IOError("контроллер ответил NAK (адрес не поддерживается или защита)")
    if raw[0] != STX or len(raw) < nbytes * 2 + 4:
        raise IOError(f"неожиданный ответ: {raw!r}")
    data = raw[1:1 + nbytes * 2]
    etx_sum = raw[1:1 + nbytes * 2 + 1]
    if raw[1 + nbytes * 2] != ETX:
        raise IOError(f"нет ETX в ответе: {raw!r}")
    got = raw[2 + nbytes * 2:4 + nbytes * 2].decode()
    if f"{sum(etx_sum) & 0xFF:02X}" != got.upper():
        raise IOError("ошибка контрольной суммы ответа")
    return [int(data[i:i + 2], 16) for i in range(0, len(data), 2)]


def d_special_addr(n):
    """Адрес специального регистра D8000..D8255 в протоколе FX."""
    return 0x0E00 + (n - 8000) * 2


class FX:
    def __init__(self, port):
        self.s = serial.Serial(port, 9600, bytesize=7, parity="E", stopbits=1, timeout=1)

    def ping(self):
        self.s.reset_input_buffer()
        self.s.write(bytes([ENQ]))
        return self.s.read(1) == bytes([ACK])

    def read_bytes(self, addr, nbytes):
        self.s.reset_input_buffer()
        self.s.write(build_read(addr, nbytes))
        raw = self.s.read(nbytes * 2 + 4)
        return parse_reply(raw, nbytes)

    def read_d(self, first, count):
        """Читает D8000+ регистры, возвращает {номер: значение}."""
        out = {}
        n = first
        while n < first + count:
            chunk = min(16, first + count - n)
            b = self.read_bytes(d_special_addr(n), chunk * 2)
            for i in range(chunk):
                out[n + i] = b[2 * i] | (b[2 * i + 1] << 8)
            n += chunk
            time.sleep(0.05)
        return out


ERR_FLAGS = {
    8060: "ошибка конфигурации ввода-вывода",
    8061: "аппаратная ошибка ПЛК",
    8062: "ошибка связи с панелью/ПК",
    8063: "ошибка последовательной связи",
    8064: "ошибка параметров",
    8065: "синтаксическая ошибка программы",
    8066: "ошибка схемы (логики) программы",
    8067: "ошибка выполнения (операции)",
}

CODES = {
    0: "нет ошибки",
    6101: "ошибка RAM",
    6102: "ошибка схемы процессора",
    6103: "ошибка шины ввода-вывода (модули расширения)",
    6104: "нет 24В на модуле расширения",
    6105: "сторожевой таймер (время цикла > D8000)",
    6106: "ошибка конфигурации ввода-вывода",
    6107: "ошибка системной шины",
    6401: "ОШИБКА КОНТРОЛЬНОЙ СУММЫ ПРОГРАММЫ — программа повреждена или стёрта (часто села батарея)",
    6402: "ошибка настройки объёма памяти",
    6403: "ошибка настройки latch-области",
    6404: "ошибка области комментариев",
    6405: "ошибка области файловых регистров",
    6406: "ошибка инициализации буферной памяти",
    6407: "ошибка специальных настроек",
    6409: "ошибка прочих параметров",
    6501: "неверная комбинация инструкции/устройства",
    6502: "нет OUT T/C перед уставкой",
    6503: "нет уставки у таймера/счётчика",
    6504: "дублирование меток P/I",
    6505: "устройство вне допустимого диапазона",
    6506: "неизвестная инструкция",
    6507: "ошибка метки P",
    6508: "ошибка прерывания I",
    6509: "прочая синтаксическая ошибка",
    6610: "LD/LDI подряд 9 и более раз",
    6611: "нет LD перед ANB/ORB",
    6612: "лишние LD без ANB/ORB",
    6613: "MPS вложен более 12 раз",
    6614: "нет MPS перед MRD/MPP",
    6617: "ошибка инструкции без условия",
    6619: "недопустимая инструкция между STL-RET / MC-MCR / I-IRET",
    6620: "слишком глубокая вложенность FOR-NEXT",
    6621: "FOR и NEXT не парные",
    6622: "нет NEXT",
    6623: "нет MCR",
    6624: "нет SRET",
    6625: "нет FEND",
    6626: "нет IRET",
    6627: "нет RET",
    6628: "MC вложен неверно",
    6629: "нет END",
    6630: "нет SRET/IRET",
    6632: "ошибка вызова подпрограммы",
}


def explain(code):
    if code in CODES:
        return CODES[code]
    if 6700 <= code < 6800:
        return "ошибка выполнения инструкции (операционная)"
    if 6500 <= code < 6600:
        return "синтаксическая ошибка"
    if 6600 <= code < 6700:
        return "ошибка схемы"
    return "см. руководство FX3U (Programming Manual, раздел Error codes)"


def main():
    if serial is None:
        sys.exit("Установите pyserial:  pip install pyserial")
    if len(sys.argv) < 2:
        sys.exit("Использование: python fx_diag.py COM3")

    plc = FX(sys.argv[1])
    print(f"Порт {sys.argv[1]}: 9600 7E1")
    if not plc.ping():
        print("ВНИМАНИЕ: нет ответа на ENQ — пробую читать всё равно...")

    d = plc.read_d(8000, 70)
    d.update(plc.read_d(8100, 3))

    print("\n=== Контроллер ===")
    print(f"D8001 тип/версия : {d[8001]}   (24xxx = FX2N/FX3U-совместимый)")
    print(f"D8101 тип/версия : {d[8101]}   (16xxx = оригинальный FX3U/FX3UC)")
    print(f"D8002 память     : {d[8002]}  (2=2k, 4=4k, 8=8k шагов, 8 = >=16k см. D8102)")
    print(f"D8102 память     : {d[8102]} k шагов")
    print(f"D8000 watchdog   : {d[8000]} мс")
    print(f"D8005 батарея    : {d[8005] / 10:.1f} В  (норма ~3.0 В; порог D8006 = {d[8006] / 10:.1f} В)")
    if 0 < d[8005] <= d[8006]:
        print("  >>> БАТАРЕЯ РАЗРЯЖЕНА — программа в RAM могла стереться!")

    print("\n=== Ошибки ===")
    print(f"D8004 активный флаг ошибки: M{d[8004]}" if d[8004] else "D8004 = 0 (флаг ошибки не установлен)")
    if d[8004] in ERR_FLAGS:
        print(f"  -> {ERR_FLAGS[d[8004]]}")
    for reg in (8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067):
        if d[reg]:
            print(f"D{reg} = {d[reg]}  [{ERR_FLAGS[reg]}]  -> {explain(d[reg])}")
    print(f"D8069 шаг программы с ошибкой: {d[8069]}")
    if d[8068]:
        print(f"D8068 шаг с ошибкой выполнения (защёлкнут): {d[8068]}")
    if not any(d[r] for r in range(8060, 8068)):
        print("Кодов ошибок в D8060-D8067 нет.")

    print("\nПришлите этот вывод целиком — по нему можно определить причину.")


if __name__ == "__main__":
    main()
