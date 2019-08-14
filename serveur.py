# Application Acoucite

import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
import json
import sqlite3
import matplotlib.pyplot as plt
from pathlib import Path


# définition du handler
class RequestHandler(http.server.SimpleHTTPRequestHandler):
    
  # On définit des variables de classes pour la mémorisation des entrées des utilisateurs et d'autres paramètres
    
  # référence de la station de mesure  
  reference = ''  
  
  # période de calcul du bruit  
  periodeGra = ''
  
  # respectivement année de début, mois de début et jour de début
  year1 = ''
  month1 = ''
  day1 = ''
  
  # respectivement année de fin, mois de fin et jour de fin
  year2 = ''
  month2 = ''
  day2 = ''
    
  # respectivement les identifiants de la date de début et de la date de fin (dans la base de données 'histo') 
  id1 = 0
  id2 = 0
  
  # respectivement les assertions "la date de début a été choisie" et "la date de fin a été choisie"
  date1choisie = False
  date2choisie = False

  # sous-répertoire racine des documents statiques
  static_dir = '/client'

  # on surcharge la méthode qui traite les requêtes GET
  def do_GET(self):
    self.init_params()

    # requete location - retourne la liste de lieux et leurs coordonnées géogrpahiques
    if self.path_info[0] == "location":
      conn = sqlite3.connect('acoucite.sqlite')
      co=conn.cursor()
      co.execute("SELECT * FROM stations")
      r = co.fetchall()
      data = [{'id':a[0], 'lat':a[6], 'lon':a[5], 'ref':a[1]} for a in r]
      self.send_json(data)

    # requete reinitialisation - (agit du côté client) : réinitialise l'interface d'entrée de l'utilisateur lorsqu'on change de station
    # requete rajoutée par soucis de clarté dans le code html
    elif self.path_info[0] == "reinitialisation":
        self.send_json({'toWrite':''})

    # requete description - retourne la description du lieu dont on passe l'id en paramètre dans l'URL
    elif self.path_info[0] == "description":
      conn = sqlite3.connect('acoucite.sqlite')
      co=conn.cursor()
      co.execute("SELECT * FROM stations")
      r = co.fetchall()
      data = [{'id':a[0], 'desc':a[2], 'date_update':a[3], 'hour_update':a[4]} for a in r]
      d_aux = [{'id':a[0], 'lat':a[6], 'lon':a[5], 'ref':a[1]} for a in r]
      id_station=int(self.path_info[1])
      for c in data:
        if c['id'] == id_station:
          for d in d_aux:
              if d['id'] == id_station:
                  RequestHandler.reference = d['ref'] # la variable globale prend la valeur de la référence de la station sélectionnée
          self.send_json(c)
          break
      
    # requete displayPeriode - retourne le script html pour afficher la liste déroulante des choix de périodes de calcul du bruit
    elif self.path_info[0] == "displayPeriode":
        # (Robustesse) On indique que les dates n'ont pas encore été choisies à ce stade
        RequestHandler.date1choisie = False
        RequestHandler.date2choisie = False
        res = self.script_periodes() # script_periodes() renvoit le script html en question
        self.send_json({'toWrite': res}) 
        
    # requete robustessePeriode - (agit du côté serveur) : indique que les dates n'ont pas encore été choisies 
    elif self.path_info[0] == "robustessePeriode":
        RequestHandler.date1choisie = False
        RequestHandler.date2choisie = False
        self.send_json({'toWrite': ''}) 
        
    # requete fromPeriodeToYears - retourne les scripts html pour afficher la liste déroulante des choix des années de début et de fin, appelée après avoir choisi la période de calcul du bruit        
    elif self.path_info[0] == "fromPeriodeToYears":
        # (Robustesse) On indique que les dates n'ont pas encore été choisies à ce stade
        RequestHandler.date1choisie = False
        RequestHandler.date2choisie = False
        # on récupère la période choisie
        RequestHandler.periodeGra = self.path_info[1]
        annees = self.years() # years() génère la liste des années pour la station choisie depuis la base de donnée
        # création du script html (les scripts - res1 pour l"année de début et res2 pour l'année de fin - sont analogues)
        res1 = '<select name="annee1" onChange="selectYear1()"><option>--- Séléctionnez l'+"'"+'année de début ---</option>'
        res2 = '<select name="annee2" onChange="selectYear2()"><option>--- Séléctionnez l'+"'"+'année de fin ---</option>'
        for an in annees:
            res1 = res1 + '<option value="' + an + '">' + an + '</option>'
            res2 = res2 + '<option value="' + an + '">' + an + '</option>'
        res1 = res1 + '</select>'
        res2 = res2 + '</select>'
        self.send_json({'toWrite1':res1, 'toWrite2':res2})
        
    # requete robustesseDate - (agit du côté serveur) : indique que la date (de début ('1') ou de fin ('2') selon l'envoi par le html) n'a pas encore été choisie
    elif self.path_info[0] == "robustesseDate":
        if self.path_info[1] == '1': # ici, il s'agit de la date de début
            RequestHandler.date1choisie = False
        else: # ici, il s'agit de la date de fin
            RequestHandler.date2choisie = False
        self.send_json({'toWrite': ''}) 
                
    # requete fromYearToMonth - retourne le script html pour afficher la liste déroulante des choix des mois (de début ou de fin selon l'envoi par le html), appelée après avoir choisi l'année (spécifiée par l'envoi html)     
    elif self.path_info[0] == "fromYearToMonth":
        res = ''  # initialisation du script html à renvoyer
        mois = [] # initialisation de la liste des mois à afficher
        if self.path_info[1] == '1': # ici, il s'agit de la date de début
            RequestHandler.date1choisie = False # on indique que la date de début n'a pas encore été choisie car le mois de début n'a pas encore été choisi
            RequestHandler.year1 = self.path_info[2] # on récupère l'année de début envoyée par le html
            mois = self.months(RequestHandler.year1) # months(year) génère la liste des mois pour la station et l'année year depuis la base de donnée
            res = '<select name="mois1" onChange="selectMonth1()"><option>--- Séléctionnez le mois de début ---</option>'
        else: # ici, il s'agit de la date de fin (fonctionnement analogue au bloc précédent)
            RequestHandler.date2choisie = False
            RequestHandler.year2 = self.path_info[2]
            mois = self.months(RequestHandler.year2)
            res = '<select name="mois2" onChange="selectMonth2()"><option>--- Séléctionnez le mois de fin ---</option>'
        # on complète le script html
        for moi in mois:
            res = res + '<option value="' + moi + '">' + moi + '</option>'
        res = res + '</select>'
        self.send_json({'toWrite':res})
        
    # requete fromMonthToDay - retourne le script html pour afficher la liste déroulante des choix des jours (de début ou de fin selon l'envoi par le html), appelée après avoir choisi le mois (spécifié par l'envoi html)    
    elif self.path_info[0] == "fromMonthToDay":
        res = '' # initialisation du script html à renvoyer
        jours = [] # initialisation de la liste des jours à afficher
        if self.path_info[1] == '1': # ici, il s'agit de la date de début
            RequestHandler.date1choisie = False # on indique que la date de début n'a pas encore été choisie car le jour de début n'a pas encore été choisi
            RequestHandler.month1 = self.path_info[2] # on récupère le mois de début envoyé par le html
            jours = self.days(RequestHandler.year1, RequestHandler.month1) # days(year, month) génère la liste des jours pour la station (variable de classe), l'année year et le mois month depuis la base de donnée
            res = '<select name="jour1" onChange="selectDay1()"><option>--- Séléctionnez le jour de début ---</option>'
        else: # ici, il s'agit de la date de fin (fonctionnement analogue au bloc précédent)
            RequestHandler.date2choisie = False
            RequestHandler.month2 = self.path_info[2]
            jours = self.days(RequestHandler.year2, RequestHandler.month2)
            res = '<select name="jour2" onChange="selectDay2()"><option>--- Séléctionnez le jour de fin ---</option>'
        # on complète le script html
        for jour in jours:
            res = res + '<option value="' + jour + '">' + jour + '</option>'
        res = res + '</select>'
        self.send_json({'toWrite':res})
        
    # requete endDate - indique au serveur que la date (de début ('1') ou de fin ('2') selon l'envoi par le html) a été choisie, 
    # et éventuellement crée l'historique associé et renvoie les codes html permettant d'afficher l'historique et les informations sur sa génération si les deux dates ont été choisies
    elif self.path_info[0] == "endDate":
        if self.path_info[1] == '1': # ici, il s'agit de la date de début
            RequestHandler.date1choisie = True # on indique que la date de début a été choisie
            RequestHandler.day1 = self.path_info[2] # on récupère le jour de début envoyé par le html
        else: # ici, il s'agit de la date de fin
            RequestHandler.date2choisie = True # on indique que la date de fin a été choisie
            RequestHandler.day2 = self.path_info[2] # on récupère le jour de fin envoyé par le html
        res = '' # initialisation du script html à renvoyer pour l'affichage de l'éventuel historique
        res2= '' # initialisation du script html à renvoyer pour l'affichage des informations sur la génération de l'historique
        # on vérifie si les deux dates ont été choisies
        if RequestHandler.date1choisie and RequestHandler.date2choisie :
                    self.graphique_acoucite() # fonction qui génère l'historique désiré en fonction des variables de classe mises à jour à partir des entrées de l'utilisateur
                    res = '<center><img class="graph" src="graphiques/fig_'+str(RequestHandler.id1)+'_'+str(RequestHandler.id2)+'_'+RequestHandler.periodeGra+'.png"></center>' # voir le formalisme du nom du fichier plus bas dans la fonction graphique_acoucite()
                    if RequestHandler.id1 == 0 and RequestHandler.id2 == 0:
                        res2 = "<i>L'historique des niveaux de bruit journaliers n'a pu être généré (voir plus bas).</i>"
                    else:
                        res2 = "<i>L'historique des niveaux de bruit journaliers a été généré (voir plus bas).</i>"
        self.send_json({'toWrite1':res,'toWrite2':res2})
        
        
    # requête générique
    elif self.path_info[0] == "service":
      self.send_html('<p>Path info : <code>{}</p><p>Chaîne de requête : <code>{}</code></p>' \
          .format('/'.join(self.path_info),self.query_string));

    else:
      self.send_static()


  # méthode pour traiter les requêtes HEAD
  def do_HEAD(self):
      self.send_static()


  # méthode pour traiter les requêtes POST - non utilisée dans l'exemple
  def do_POST(self):
    self.init_params()

    # requête générique
    if self.path_info[0] == "service":
      self.send_html(('<p>Path info : <code>{}</code></p><p>Chaîne de requête : <code>{}</code></p>' \
          + '<p>Corps :</p><pre>{}</pre>').format('/'.join(self.path_info),self.query_string,self.body));

    else:
      self.send_error(405)


  # on envoie le document statique demandé
  def send_static(self):

    # on modifie le chemin d'accès en insérant le répertoire préfixe
    self.path = self.static_dir + self.path

    # on calcule le nom de la méthode parent à appeler (do_GET ou do_HEAD)
    # à partir du verbe HTTP (GET ou HEAD)
    method = 'do_{}'.format(self.command)

    # on traite la requête via la classe parent
    getattr(http.server.SimpleHTTPRequestHandler,method)(self)


  # on envoie un document html dynamique
  def send_html(self,content):
     headers = [('Content-Type','text/html;charset=utf-8')]
     html = '<!DOCTYPE html><title>{}</title><meta charset="utf-8">{}' \
         .format(self.path_info[0],content)
     self.send(html,headers)

  # on envoie un contenu encodé en json
  def send_json(self,data,headers=[]):
    body = bytes(json.dumps(data),'utf-8') # encodage en json et UTF-8
    self.send_response(200)
    self.send_header('Content-Type','application/json')
    self.send_header('Content-Length',int(len(body)))
    [self.send_header(*t) for t in headers]
    self.end_headers()
    self.wfile.write(body) 

  # on envoie la réponse
  def send(self,body,headers=[]):
     encoded = bytes(body, 'UTF-8')

     self.send_response(200)

     [self.send_header(*t) for t in headers]
     self.send_header('Content-Length',int(len(encoded)))
     self.end_headers()

     self.wfile.write(encoded)


  # on analyse la requête pour initialiser nos paramètres
  def init_params(self):
    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = info.path.split('/')[1:]
    self.query_string = info.query
    self.params = parse_qs(info.query)

    # récupération du corps
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' : 
        self.params = parse_qs(self.body)
    else:
      self.body = ''

    print(length,ctype,self.body, self.params)
    

  # la fonction suivante renvoie le script permettant d'afficher la liste déroulante du choix de périodes
  def script_periodes(self):
      periodes = ['lday', 'lden', 'levening', 'lnight']
      desc_periodes = ['Période diurne (6h-18h)','Périodes horaires jour (6h-18h), soirée (18h-22h) et nuit (22h-6h)','Période horaire 18h-22h','Période nocturne (22h-6h)']
      res = '<select name="periodeMesure" onChange="selectPeriode()"><option>--- Sélectionnez une période ---</option>'
      for i in range(4):
          res = res + '<option value="' + periodes[i] + '">' + desc_periodes[i] + '</option>'
      res = res + '</select>'
      return res
    
  # la fonction suivante renvoie la liste des années pour lesquelles la station choisie (variable de classe) dispose de mesures de bruit pour la période choisie (voir requête SQL)
  def years(self):
        # connexion à la base de données  
        conn = sqlite3.connect('acoucite.sqlite')
        co=conn.cursor()
        # (Robustesse) il faut travailler sur la base de données où sont disponibles les mesures pour la période séléctionnée, d'où le test avec 'None' (voir énoncé)
        co.execute("SELECT DISTINCT time_year FROM histo WHERE ref = '"+RequestHandler.reference+"' AND "+RequestHandler.periodeGra+" != 'None'")
        r_aux=co.fetchall()
        return [a[0] for a in r_aux]
        
  # la fonction suivante renvoie la liste des mois pour lesquelles la station choisie (variable de classe) dispose de mesures de bruit pour la période choisie, pour l'année year (voir requête SQL)
  def months(self, year):
        # connexion à la base de données 
        conn = sqlite3.connect('acoucite.sqlite')
        co=conn.cursor() 
        # (Robustesse) il faut travailler sur la base de données où sont disponibles les mesures pour la période séléctionnée, d'où le test avec 'None' (voir énoncé)
        co.execute("SELECT DISTINCT time_month FROM histo WHERE ref = '"+RequestHandler.reference+"' AND time_year = '"+year+"' AND "+RequestHandler.periodeGra+" != 'None'")
        r_aux=co.fetchall()
        return [a[0] for a in r_aux]

  # la fonction suivante renvoie la liste des jours pour lesquelles la station choisie (variable de classe) dispose de mesures de bruit pour la période choisie, pour l'année year et le mois month (voir requête SQL)
  def days(self, year, month):
        # connexion à la base de données 
        conn = sqlite3.connect('acoucite.sqlite')
        co=conn.cursor()    
        # (Robustesse) il faut travailler sur la base de données où sont disponibles les mesures pour la période séléctionnée, d'où le test avec 'None' (voir énoncé)
        co.execute("SELECT time_day FROM histo WHERE ref = '"+RequestHandler.reference+"' AND time_year = '"+year+"' AND time_month = '"+month+"' AND "+RequestHandler.periodeGra+" != 'None'")
        r_aux=co.fetchall()
        return [a[0] for a in r_aux]
        
  # la fonction suivante crée, lorsque la date de début est strictement antérieure à la date de fin, l'historique de bruit correspondant pour la période de mesure choisie (variable globale)      
  def graphique_acoucite(self):      
      
        periodes = ['lday', 'lden', 'levening', 'lnight'] # periodes de mesures
        desc_periodes = ['la période diurne (6h-18h)','les périodes horaires jour (6h-18h), soirée (18h-22h) et nuit (22h-6h)','la période horaire 18h-22h','la période nocturne (22h-6h)'] # description des périodes
    
        ind = periodes.index(RequestHandler.periodeGra) # on récupère l'indice de la période choisie dans la lite des périodes pour avoir accès à la description correspondante dans desc_periodes
        
        # connexion à la base de données
        conn = sqlite3.connect('acoucite.sqlite')
        co=conn.cursor()

        # requête permettant de renvoyer l'identifiant de la ligne correspondante à la date de début pour la station choisie
        co.execute("SELECT id FROM histo WHERE ref = '" + RequestHandler.reference + "' AND time_year = '" + RequestHandler.year1 + "' AND time_month = '" + RequestHandler.month1 + "' AND time_day = '" + RequestHandler.day1 + "' AND "+RequestHandler.periodeGra+" != 'None'")
        r_aux = co.fetchall()

        RequestHandler.id1 = r_aux[0][0] # identifiant de la ligne correspondante à la date de début

        # requête permettant de renvoyer l'identifiant de la ligne correspondante à la date de fin pour la station choisie
        co.execute("SELECT id FROM histo WHERE ref = '" + RequestHandler.reference + "' AND time_year = '" + RequestHandler.year2 + "' AND time_month = '" + RequestHandler.month2 + "' AND time_day = '" + RequestHandler.day2 + "' AND "+RequestHandler.periodeGra+" != 'None'")
        r_aux = co.fetchall()
        
        RequestHandler.id2 = r_aux[0][0] # identifiant de la ligne correspondante à la date de fin
        
        # --- formalisme de nommage des historiques ---
        # dans la suite, les historiques sont sauvés sous le nom significatif : "fig_id1_id2_periodeGra.png"
        # ce qui est justifié par le fait que id1 et id2 sont des clé primaires dans la table, 
        # et que les valeurs de niveaux sonores choisies sont déterminées par la période de mesure choisie
        # on rappelle que quelle que soit la période periodeGra, l'image : ""fig_0_0_periodeGra.png" désigne un message d'erreur
        
        if RequestHandler.id1 >= RequestHandler.id2 : # si cela est vérifié, cela signifie que l'on n'a pas la stricte antériorité de la date de début par rapport à celle de fin
            RequestHandler.id1 = 0
            RequestHandler.id2 = 0
            # ces dernières valeurs ont été choisies afin de générer le message d'erreur
        else : # on est dans le cas où on peut générer un historique
            my_file = Path('client/graphiques/fig_'+str(RequestHandler.id1)+'_'+str(RequestHandler.id2)+'_'+RequestHandler.periodeGra+'.png')
            graphExiste = my_file.is_file() # vaut True si l'historique existe déjà, False sinon, afin de ne pas recréer un historique déjà disponible
            
            if not(graphExiste): 
                co.execute("SELECT time_year, time_month, time_day, " + RequestHandler.periodeGra + " FROM histo WHERE id <= " + str(RequestHandler.id2) + " AND id >= " + str(RequestHandler.id1) + " AND "+RequestHandler.periodeGra+" != 'None'")
                r_aux = co.fetchall()
            
                mois = ['Jan','Fév','Mar','Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sept', 'Oct', 'Nov', 'Déc']
                division = max((RequestHandler.id2-RequestHandler.id1)//5, 1)
                non_divisible = 1
                if len(r_aux)%division == 0 :
                    non_divisible = 0
                xticks = [n*division for n in range(len(r_aux)//division + 1*non_divisible)]
                xlabels = ['{} {} {}'.format(int(a[2]), mois[int(a[1])-1], int(a[0])) for a in [r_aux[t] for t in xticks]]
                    
                x=range(0,len(r_aux))
                y=[a[-1] for a in r_aux]
                    
                plt.figure(figsize=(15,8))
                plt.grid(which='major', color='#888888', linestyle='-')
                plt.grid(which='minor',axis='x', color='#888888', linestyle=':')
                plt.title('\nNiveau sonore (en dB) calculé à partir des mesures de la station '+RequestHandler.reference+' entre le '+RequestHandler.day1+'/'+RequestHandler.month1+'/'+RequestHandler.year1+' et le '+RequestHandler.day2+'/'+RequestHandler.month2+'/'+RequestHandler.year2+'\nsur '+desc_periodes[ind]+'\n',fontsize=13)
                
                ax = plt.subplot(111)
                ax.set_xticks(xticks)
                ax.set_xticks(x, minor=True)
                ax.set_xticklabels(xlabels, fontsize=12)
                
                plt.xlabel('Date')
                plt.ylabel('Niveau sonore calculé (en dB)')
                    
                plt.plot(x,y)
                plt.savefig("client/graphiques/fig_"+str(RequestHandler.id1)+"_"+str(RequestHandler.id2)+"_"+RequestHandler.periodeGra)
      
        
# instanciation et lancement du serveur
httpd = socketserver.TCPServer(("", 8080), RequestHandler)
httpd.serve_forever()
