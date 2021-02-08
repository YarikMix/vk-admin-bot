from pytils import numeral


def get_time(n):
    h = ""
    m = ""
    s = ""
    if n >= 3600:
        h = "{} ".format(numeral.get_plural(n // 3600, "час, часа, часов"))
    else:
        if n >= 60:
            m = "{} ".format(numeral.get_plural(n // 60 % 60, "минута, минуты, минут"))
        s = numeral.get_plural(n % 60, "секунда, секунды, секунд")
    return h + m + s