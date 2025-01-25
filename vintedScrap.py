import os
import re
import discord
import asyncio
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


# map de stockage des marques et prix 
price_and_brand = {}


# Crée une instance de bot
intents = discord.Intents.all()
intents.messages = True

#initialise le driver/navigateur 
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

#// Fonction pour lancer le navigateur dans un thread(selenium)
#// avec les options mentionner au dessus 
#// --headless = mode sans interface graphique
#// --no-sandbox = Désactive l'isolation de sécurité de Chrome 
#// --disable-dev-shm-usage = Désactive l'utilisation de la mémoire partagée
def start_selenium():
    driver = webdriver.Chrome(options=chrome_options)
    return driver




#//definit le prefixe '!' comme etant le prefixe de base des commandes du bot discord
bot = commands.Bot(command_prefix='!', intents=intents)



#// prend la marque extrait de la page de recherche pour faire un match_case(techniques a ameliore)
#// pour ne sortir que les items en lien avec la demande utilisateur
#// renvoie 0 pour un match et 1 pour un non match
def get_match(brand_match, price):
  try :
    price_match = int(get_title(price))
  except ValueError :
     price_match = 999999  
  for brand in price_and_brand:
      if brand.lower() == brand_match.lower():
          if price_and_brand[brand] >= price_match:
            return 0
  return 1



  
#// simple debug function to display price_and_brand::map
def display_price_and_brand() :
    for brand in price_and_brand:
        print(f"{brand}: {price_and_brand[brand]}")




# // methode cree car je n'arrivais pas a extraire la sous-chaine que je souhaitais avec les methodes 
# // python classique
# // prend la chaine extrait du titre de l'item et renvoie une nouvelle chaine a la premiere 
# // virgule rencontre
def get_title(input_str):
  i = 0
  for char in input_str:
      if char == ',':
          break
      i += 1
  new_str = input_str[:i]  # Prend la sous-chaîne jusqu'à l'indice i
  return new_str




# // initialise la map price_and_brand avec l'entre utilisateur des marques et prix a verifier
def init_request(arg):
    paires = arg.split(',')
    for paire in paires :
        brand, valeur = paire.split(':')
        price_and_brand[brand] = int(valeur)



@bot.command()
async def fcktest(ctx):
    await ctx.send("yo!!")



# @bot.command()
# async def ShowList():



@bot.command()
async def lunchScrap(ctx, arg: str = None):

  if arg is None:
    await ctx.send("Tu dois fournir une URL après la commande ! Exemple: `!lunchScrap http://example.com`.")
    return
  else:
    init_request(arg)
    display_price_and_brand()
    await ctx.send("liste de monitoring charger, je me mets a chercher vos articles")


  
  visited_items = set() # set to keep track of visited items
  driver = await bot.loop.run_in_executor(None, start_selenium)
  
  while True:

    if len(visited_items) > 5000 : 
      # Convertir l'ensemble en liste
      item_list = list(visited_items)
      half = len(item_list) // 2
      visited_item = set(item_list[:half])


    driver.get('https://www.vinted.fr/catalog?time=1732785164&catalog[]=5&order=newest_first&catalog_from=0&page=1')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'new-item-box__overlay--clickable')))

    
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    grid_items = soup.find_all('a')
    
    for item in grid_items:
      href = item.get('href')  # Assurez-vous que c'est bien un lien
      
      if href and href.startswith('https://www.vinted.fr/items/'): #ATTENTION A L'EXTENSION DU PAYS
        
        if href in visited_items:
          continue
          
        visited_items.add(href)
        #print(item.prettify())

        data = item.get('title')
        brand_match = re.search(r'marque\s*:\s*([^,]+)', data)
        brand_match = brand_match.group(1)
        price_amount = re.search(r'prix\s*:\s*([\d,]+)\s*€', data)
        if price_amount :
            price_amount = price_amount.group(1)
        else :
           print("error with price!!!")
           print(data)
        

        if get_match(brand_match) == 0: # si le match est bon
          
          driver.get(href)
          item_page = driver.page_source
          item_soup = BeautifulSoup(item_page, 'html.parser')
          publish_time = item_soup.find('div', class_='details-list__item-value', itemprop='upload_date').text.strip()

          
          #// voir doc partie 1
          int_publish_time = 30
          if "A l'instant" != publish_time:
            
            splitted_string = publish_time.split()
            
            if splitted_string[3].isdigit():
              int_publish_time = int(splitted_string[3])
            else :
              int_publish_time = 1

          
          if "A l'instant" == publish_time or int_publish_time <= 20:
            
            post_title = get_title(data)
            

            #recuperation des images apres avoir naviguer sur la page de chaque items
            images = item_soup.find_all('img', alt=re.compile(rf'^{re.escape(post_title)}'))
            
            print(f"longueur de retour des images trouver {len(images)}")

            if price_amount :
              
              img_url = [] #variable de stockage des url d'images
              for i, img in enumerate(images):
                if i < 3:  # Limiter à 3 images
                  img_url.append(img.get('src'))

              price_currency = "EUR" # A REVOIR
              #print(publish_time, brand_match, post_title, href, price_amount)

              embed = discord.Embed(title=post_title, color=0x72d345, url=href)
              embed.set_image(url=img_url[0])
              embed.add_field(name="Brand : ", value=brand_match, inline=False)
              embed.add_field(name="Price : ", value=price_amount, inline=False)

              embeds = [embed]

              for i in range(1, len(img_url)):
                if img_url[i]:
                  embed_img = discord.Embed(url=href)
                  embed_img.set_image(url=img_url[i])
                  embeds.append(embed_img)
              
              #except Exception as e:
              #  print(f"images exeption catch :{str(e)}")
                
              await ctx.send(embeds = embeds)
              with open('log/price.txt', 'a') as f:
                print('------------------------------------', file=f)
                print('link =', href, file=f)
                print('brand =', brand_match, file=f)
                print('price =', price_amount, file=f)
                print('curr =', price_currency, file=f)
                print('publish_time =', publish_time, file=f)
                print('post_title =', post_title, file=f)
                print('img_url[0] =', img_url[0], file=f)
    print(f"longueur des items en memoire = {len(visited_items)}")
    await ctx.send("J'AI FINIS DE FAIRE LE TOUR")
    await asyncio.sleep(6)
    
BOT_TOKEN = os.environ['BOT_TOKEN']

bot.run(BOT_TOKEN)