import random



RARITIES = {

    "Commune": 60,
    "Peu commune": 25,
    "Rare": 10,
    "Ultra Rare": 4,
    "Secrète": 1

}



def get_rarity():

    pool=[]


    for key,value in RARITIES.items():

        pool += [key]*value


    return random.choice(pool)