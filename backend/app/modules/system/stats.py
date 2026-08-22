"""CPU kullanim yuzdesi.

/proc/stat kumulatif jiffy sayaclari tutar; anlik yuzde ancak iki okuma
arasindaki FARKTAN cikar. Bu yuzden son okuma modul icinde saklanir.

Ilk cagriya verilecek dogru bir cevap yok (fark alacak onceki olcum yok);
o cagri None doner ve arayuz "olculuyor" gosterir -- sifir uydurmaz.
"""
from __future__ import annotations

_previous: tuple[int, int] | None = None


def _read() -> tuple[int, int] | None:
    """(bos_olmayan_jiffy, toplam_jiffy). Okunamazsa None."""
    try:
        with open("/proc/stat") as handle:
            line = handle.readline()
    except OSError:
        return None
    if not line.startswith("cpu "):
        return None
    fields = [int(value) for value in line.split()[1:]]
    if len(fields) < 5:
        return None
    total = sum(fields)
    # user nice system [idle iowait] irq softirq steal ...
    idle = fields[3] + fields[4]
    return total - idle, total


def cpu_percent() -> float | None:
    """Bir onceki cagridan bu yana gecen surenin CPU kullanim yuzdesi."""
    global _previous

    current = _read()
    if current is None:
        return None

    previous, _previous = _previous, current
    if previous is None:
        return None

    busy_delta = current[0] - previous[0]
    total_delta = current[1] - previous[1]
    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * busy_delta / total_delta))
