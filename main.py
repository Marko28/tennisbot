import keep_alive
import discord
import time
import asyncio
import random
import os
import pymongo, dns

client = discord.Client()

def isNewPlayer(the_author, mycol):
    the_id, the_name = the_author.id, the_author.name
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    if mydoc:
        return False
    mydict = {"id": the_id,
    "name": the_name,
    "level": 2,
    "opp lvl": 1,
    "opp change": 1,
    "in match": False,
    "xp gain": 0
    }
    mycol.insert_one(mydict)
    return True

def getPlayerLevel(the_author, mycol):
    the_id = the_author.id
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    return mydoc["level"]

def setPlayerLevel(the_id, lvl, lvlDecr, mycol):
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    newvalues = {"$set": {"level": lvl,
    "xp gain": lvlDecr}}
    mycol.update_one(myquery, newvalues)

def isPlayerInMatch(the_author, mycol):
    the_id = the_author.id
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    return mydoc["in match"]

def togglePlayerMatch(the_author, mycol):
    the_id = the_author.id
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    in_match = not mydoc["in match"]
    newvalues = {"$set": {"in match": in_match}}
    mycol.update_one(myquery, newvalues)
    return

def allPlayerMatchesOff(mycol):
    newvalues = {"$set": {"in match": False}}
    mycol.update_many(dict(), newvalues)
    return

def getOpponentLevel(the_author, mycol):
    the_id = the_author.id
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    return mydoc["opp lvl"]

def getOpponentChange(the_author, mycol):
    the_id = the_author.id
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    return mydoc["opp change"]

async def setOpponentLevel(the_message, matchWon, mycol):
    the_author, the_channel = the_message.author, the_message.channel
    the_id, player = the_author.id, the_author.display_name
    opp_lvl, opp_change = getOpponentLevel(the_author, mycol), getOpponentChange(the_author, mycol)
    if (matchWon):
        if (opp_change < 1):
            opp_change = 1
        opp_lvl += opp_change
        opp_change += 1
    else:
        if (opp_change > -1):
            opp_change = -1
        opp_lvl += opp_change
        opp_change -= 1
        if (opp_lvl < 1):
            opp_lvl = 1
            opp_change = -1
    await the_channel.send(
        f"{player}, your next opponent will be level {opp_lvl}.")
    myquery = {"id": the_id}
    newvalues = {"$set": {"opp lvl": opp_lvl,
    "opp change": opp_change}}
    mycol.update_one(myquery, newvalues)
    return

def shortenName(player):
    n = len(player)
    if (n > 10):
        return player[:10]
    return player + ' ' * (10 - n)

def printGame(n):
    if (n == 0):
        return "0"
    elif (n == 1):
        return "15"
    elif (n == 2):
        return "30"
    elif (n == 6):
        return "Ad"
    elif (n >= 10):
        return f"{n-10}"
    else:  # 3 is 40, 4 is deuce, 5 is disadvantage
        return "40"

def printScores(names, sets, game, serv):
    p_s = "  ".join([str(x) for x in sets[0]])
    o_s = "  ".join([str(x) for x in sets[1]])
    p_g = printGame(game[0])
    o_g = printGame(game[1])
    S = [f"`{names[0]}\t{p_s}  |  {p_g}`", f"`{names[1]}\t{o_s}  |  {o_g}`"]
    S[serv] += "\t:tennis:"
    return S

def countSets(sets):
    # assume each set has a winner
    count = [0, 0]
    for i in range(len(sets[0])):
        if (sets[0][i] == 7):
            count[0] += 1
            continue
        elif (sets[1][i] == 7):
            count[1] += 1
            continue
        elif (sets[0][i] == 6):
            count[0] += 1
        else:
            count[1] += 1
    if (count[0] == 2):
        return 0
    if (count[1] == 2):
        return 1
    return -1

def isMatchWon(winner, sets):
    S = " won a game!"
    matchWon = -1
    sets[winner][-1] += 1
    if (sets[winner][-1] == 7
        or (sets[winner][-1] == 6 and sets[1 - winner][-1] < 5)):
        S = " won the match! :trophy:"
        matchWon = countSets(sets)
        if (matchWon == -1):
            S = " won a set!!!"
            sets[0].append(0)
            sets[1].append(0)
    return matchWon, sets, S

def getWinner(lvls, serv):
    x = random.uniform(0, 1)
    if (x < 0.1):  # ace
        return serv
    x = random.uniform(0, 1)
    if (x < 0.03):  # double fault
        return 1 - serv
    servMult = random.uniform(1, 2)
    x = [random.uniform(0, lvls[0]), random.uniform(0, lvls[1])]
    x[serv] *= servMult
    while x[0] > 1 and x[1] > 1:
        x = [random.uniform(0, x[0]), random.uniform(0, x[1])]
    return x.index(max(x))

def getOpponentName(lvl, mycol2):
    myquery = {"id": lvl}
    mydoc = list(mycol2.find(myquery))
    if not mydoc:
        return "tennisbot"
    mydoc = mydoc[0]
    return mydoc["name"]

def getLevelDecrement(the_author, mycol):
    the_id = the_author.id
    myquery = {"id": the_id}
    mydoc = list(mycol.find(myquery))
    mydoc = mydoc[0]
    return mydoc["xp gain"]

async def simulateExp(the_message, lvls, mycol):
    the_author, the_channel = the_message.author, the_message.channel
    the_id, player = the_author.id, the_author.display_name
    # lvls[1] opportunites for a 1 in lvl[0]^2 chance to level up.
    if (lvls[1] == 1):
        o = "opportunity"
    else:
        o = "opportunities"
    S = f"{lvls[1]} {o} to level up."
    await the_channel.send(S)
    M = await the_channel.send("_ _")
    s = []
    for i in range(lvls[1]):
        await asyncio.sleep(i + 1)
        lvls[1] -= 1
        chance = lvls[0]**2 - lvls[2]
        if (chance <= 0):
            chance = 1
        if (random.uniform(0, chance) < 1):
            lvls[0] += 1
            s.append(
                f"`{i+1}: 1 in {chance} chance to level up suceeded.`\n{player}, you are now level {lvls[0]}\n"
            )
            lvls[2] = 0
        else:
            s.append(f"`{i+1}: 1 in {chance} chance to level up failed.`\n")
            lvls[2] += 1
        await M.edit(content=''.join(s))
    await the_channel.send(f"{player}, your tennis skill level is {lvls[0]}.")
    setPlayerLevel(the_id, lvls[0], lvls[2], mycol)
    for i in range(len(s) - 1):
        await asyncio.sleep(i + 1)
        s = s[1:]
        await M.edit(content=''.join(s))
    await asyncio.sleep(lvls[0])
    await M.delete()

def isGameWon(winner, game):
    gameWon = False
    if (game[winner] == 0 or game[winner] == 1):
        game[winner] += 1
    elif (game[winner] == 2):
        if (game[1 - winner] == 3):
            game = [4, 4]
        else:
            game[winner] += 1
    elif (game[winner] == 3 or game[winner] == 6):
        gameWon = True
        game = [0, 0]
    elif (game[winner] == 4):
        game[winner], game[1 - winner] = 6, 5
    elif (game[winner] == 5):
        game = [4, 4]
    else:  # tiebreak
        game[winner] += 1
        if (game[winner] >= 17 and game[winner] - game[1 - winner] >= 2):
            game = [0, 0]
            gameWon = True
    return gameWon, game

def simulatePoint(lvls, sets, game, serv):
    winner = getWinner(lvls, serv)
    matchWon = -1
    S = " won a point."
    gameWon, game = isGameWon(winner, game)
    if (game[0] + game[1] > 20 and (game[0] + game[1]) % 2 == 1):
        serv = 1 - serv
    if (gameWon):
        matchWon, sets, S = isMatchWon(winner, sets)
        if (isTieBreakGame(sets)):
            game = [10, 10]
        if (game[0] + game[1] > 20):
            serv = whoServedTieBreakGame(game, serv)
        serv = 1 - serv
    return matchWon, sets, game, serv, winner, S

def isTieBreakGame(sets):
    return sets[0][-1] == 6 and sets[1][-1] == 6

def whoServedTieBreakGame(game, serv):
    points = game[0] + game[1]
    if (points % 4 == 0 or points % 4 == 3):
        return serv
    return 1 - serv

async def simulateMatch(the_message, mycol, mycol2):
    the_author, the_channel = the_message.author, the_message.channel
    player = the_author.display_name
    lvls = [
        getPlayerLevel(the_author, mycol),
        getOpponentLevel(the_author, mycol),
        getLevelDecrement(the_author, mycol)
    ]
    players = [player, getOpponentName(lvls[1], mycol2)]
    await the_channel.send(
        f"**{players[0]}** (level {lvls[0]})\tv\t**{players[1]}** (level {lvls[1]})"
    )
    names = [shortenName(players[0]), shortenName(players[1])]
    matchWon = -1
    sets = [[0], [0]]
    game = [0, 0]
    serv = random.randint(0, 1)
    S1 = printScores(names, sets, game, serv)
    M1 = await the_channel.send(S1[0] + '\n' + S1[1])
    M2 = await the_channel.send("Match is starting:\t\t5")

    for i in range(5):
        await asyncio.sleep(1)
        await M2.edit(content=f"Match is starting:\t{5-1-i}")

    while (matchWon == -1):
        matchWon, sets, game, serv, winner, S2 = simulatePoint(
            lvls, sets, game, serv)
        S1 = printScores(names, sets, game, serv)
        rally_t = random.randint(1,lvls[0]+lvls[1])
        await asyncio.sleep(rally_t)
        await M2.edit(content=f"{rally_t} shot rally.\n"+players[winner] + S2)
        await M1.edit(content=S1[0] + '\n' + S1[1])

    await M1.edit(
        content=
        f"`{names[0]}\t{'  '.join([str(x) for x in sets[0]])}`\n`{names[1]}\t{'  '.join([str(x) for x in sets[1]])}`"
    )
    await M2.delete()
    S2 = f"{players[winner]} won the match against {players[1-winner]}!"
    if (winner == 0):
        S2 += " :trophy:"
    await the_channel.send(S2)
    if (matchWon == 0):
        await simulateExp(the_message, lvls, mycol)
        await setOpponentLevel(the_message, True, mycol)
    else:
        await setOpponentLevel(the_message, False, mycol)

def addWhiteSpaceName(name, nChar):
    if (len(name) >= nChar):
        return name
    return name + ' ' * (nChar - len(name))

async def printRank(the_channel, client, mycol):
    mydoc = mycol.find().sort([("level", pymongo.DESCENDING), ("xp gain", pymongo.DESCENDING)])
    names, lvls, xps = [], [], []
    for x in mydoc:
        the_id = x["id"]
        the_user = await client.fetch_user(the_id)
        names.append(the_user.display_name)
        lvls.append(x["level"])
        xps.append(x["xp gain"])

    nChar = len(max(names, key=len))
    S = "Rankings:\n```"
    for i in range(len(names)):
        S += f"{i+1:2d}."
        S += f" {addWhiteSpaceName(names[i], nChar)}    {lvls[i]+xps[i]/lvls[i]**2:.2f}\n"
    S += "```"
    await the_channel.send(S)

async def printOpponentList(the_channel, mycol2):
    mydoc = mycol2.find().sort("id")
    names, lvls = [], []
    for x in mydoc:
        names.append(x["name"])
        lvls.append(x["id"])
    nChar = len(str(max(lvls)))
    S = "List of opponent players:\n```"
    for i in range(len(names)):
        S += f"{lvls[i]:2d}. {addWhiteSpaceName(names[i], nChar)}\n"
    S += "```"
    M1 = await the_channel.send(S)
    M2 = await the_channel.send("Deleting message in 10")
    for i in range(9):
        await asyncio.sleep(1)
        await M2.edit(content=f"Deleting message in {9-i}.")
    await M1.delete()
    await M2.delete()

def getHelpMessage():
    S = "Type: !tennis command\n```"
    commands = [
        "help", "play", "level", "rank", "opp list", "opp add"
    ]
    info = ["list of commands", "starts a match", "prints tennis skill level", \
    "prints rank leaderboard", "prints opponents list", "creates an opponent"]
    nChar = len(max(commands, key=len))
    for i in range(len(commands)):
        S += f"{addWhiteSpaceName(commands[i], nChar)}  {info[i]}\n"
    S += "```"
    return S

def writeNewOpponent(name, lvl):
    names, lvls = readOpponents()
    names.append(name)
    lvls.append(lvl)
    writeOpponents(names, lvls)

def getOpponentIndicesFromLevel(lvl):
    names, lvls = readOpponents()
    lvl = int(lvl)
    n = lvls.count(lvl)
    I = [0] * n
    for i in range(n):
        I[i] = lvls.index(lvl)
        lvls[I[i]] = -1
    return I

dbpassword = os.environ.get("PYMONGO_SECRET")
dbname = "test"
client_db = pymongo.MongoClient(f"mongodb+srv://koko28:{dbpassword}@cluster0.s86qj.mongodb.net/{dbname}?retryWrites=true&w=majority")

db = client_db["TennisBot"]
mycol = db["Users"]
mycol2 = db["Opponents"]

allPlayerMatchesOff(mycol)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    the_content, the_author, the_channel = message.content, message.author, message.channel
    display_name = message.author.display_name
    if the_content == "!t" or the_content == "!tennis":
        if (isNewPlayer(the_author, mycol)):
            await the_channel.send("Welcome to the world of tennis!")
        await the_channel.send(
            f"**{display_name}**\nTennis skill level:\t\t{getPlayerLevel(the_author, mycol)}"
        )
        await the_channel.send("Type: !tennis help")
        
    elif the_content == "!t help" or the_content == "!tennis help":
        S = getHelpMessage()
        await the_channel.send(S)

    elif the_content == "!t level" or the_content == "!tennis level":
        await the_channel.send(
            f"**{display_name}**\nTennis skill level:\t\t{getPlayerLevel(the_author, mycol)}"
        )

    elif the_content == "!t play" or the_content == "!tennis play":
        if (isNewPlayer(the_author, mycol)):
            await the_channel.send("Welcome to the world of tennis!")
        if (isPlayerInMatch(the_author, mycol)):
            await the_channel.send(
                f"{display_name}, you are currently playing in a tennis match."
            )
            return
        togglePlayerMatch(the_author, mycol)
        await simulateMatch(message, mycol, mycol2)
        togglePlayerMatch(the_author, mycol)

    #ADMIN
    elif the_content == "!tennis matches off":
        if (the_author.mention == "<@383515447980589056>"):
            allPlayerMatchesOff(mycol)
        else:
            await the_channel.send("You are not bot owner.")

    elif the_content == "!t rank" or the_content == "!tennis rank":
        await printRank(the_channel, client, mycol)

    elif the_content == "!t opp list" or the_content == "!tennis opp list":
        await printOpponentList(the_channel, mycol2)

    elif message.content == "!t opp add" or message.content == "!tennis opp add":

        def fromAuthor_isDigit(m):
            return m.author == message.author and m.content.isdigit()

        def fromAuthor(m):
            return m.author == message.author

        try:
            M1 = await message.channel.send("Enter level:")
            P1 = await client.wait_for(
                'message', check=fromAuthor_isDigit, timeout=10.0)
        except:
            return await message.channel.send("Try again.")
        await M1.delete()
        try:
            M2 = await message.channel.send("Enter opponent's name:")
            P2 = await client.wait_for(
                'message', check=fromAuthor, timeout=10.0)
        except:
            return await message.channel.send("Try again.")
        await M2.delete()
        writeNewOpponent(P2.content, P1.content)

    elif message.content == "!t opp remove" or message.content == "!tennis opp remove":

        def fromAuthor_isDigit(m):
            return m.author == message.author and m.content.isdigit()

        try:
            M1 = await message.channel.send("Enter level:")
            P1 = await client.wait_for(
                'message', check=fromAuthor_isDigit, timeout=10.0)
        except:
            return await message.channel.send("Try again.")
        await M1.delete()
        try:
            names, lvls = readOpponents()
            I = getOpponentIndicesFromLevel(P1.content)
            S = "```"
            n = 1
            for i in I:
                S += f"{n}.  {names[i]}\n"
                n += 1
            S += "```\n"
            M2 = await message.channel.send(
                S + "Enter index of opponent to remove:")
            P2 = await client.wait_for(
                'message', check=fromAuthor_isDigit, timeout=10.0)
            del names[I[int(P2.content) - 1]]
            del lvls[I[int(P2.content) - 1]]
            writeOpponents(names, lvls)
        except:
            return await message.channel.send("Try again.")
        await M2.delete()

keep_alive.keep_alive()

token = os.environ.get("DISCORD_BOT_SECRET")
client.run(token)
