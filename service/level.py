import math


def xp_needed(level):

    return level * 100



def add_xp(user, amount):

    xp = user.get(
        "xp",
        0
    )

    level = user.get(
        "level",
        1
    )


    xp += amount


    leveled_up = False


    while xp >= xp_needed(level):

        xp -= xp_needed(level)

        level += 1

        leveled_up = True



    return {
        "xp": xp,
        "level": level,
        "leveled_up": leveled_up
    }