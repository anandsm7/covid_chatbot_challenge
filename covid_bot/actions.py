
from typing import Dict, Text, Any, List, Union, Optional

from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet,FollowupAction
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormAction
import requests
import ast
import pandas as pd
import json
import Parameters as params
import smtplib 
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText 
from email.mime.base import MIMEBase 
from email import encoders 
import pymongo

REQUESTED_SLOT = "requested_slot"

#initial dataframe loading
res_df = pd.read_csv('result.csv')
df_codes = pd.read_csv('countries.csv')

FORM_NAME = None

#To fetch covid search results
class Action_Covid(Action):
    def name(self):
        return "action_covid"

    #to handle api calls 
    @staticmethod
    def country_api(country_lst):
        covid_res = []

        #when user doesn't provide country name
        if len(country_lst)<1:
            country_lst = df_codes['name'].values
        for country in country_lst:
            url = "https://coronavirus-info.p.rapidapi.com/country"
            #to handle countries like UK,USA,UAE...etc
            if len(country)>4:
                country_name = country.title()
            else:
                country_name = country.upper()
            querystring = {"name": country_name}
            headers = {
                  'x-rapidapi-host': "coronavirus-info.p.rapidapi.com",
                  'x-rapidapi-key': "add-your-rapid-api-key here"}

            response = requests.request("GET", url, headers=headers, params=querystring)
            res = json.loads(response.text)
            covid_res.append(res)

        return covid_res

    #get complete covid statistics in dataframe
    @staticmethod 
    def get_res_df(res):
        data = dict()
        lst_country = []
        lst_total_cases = []
        lst_total_deaths = []
        lst_total_recovered = []
        lst_lat = []
        lst_lon = []
        text_lst = []

        for i in res:
            if(i['ok']):
                lst_country.append(i['country']['country_name'])
                lst_total_cases.append(i['country']['total_cases'])
                lst_total_deaths.append(i['country']['total_deaths'])
                lst_total_recovered.append(i['country']['total_recovered'])
                lst_lat.append(df_codes[df_codes["name"]==i['country']['country_name']]['latitude'].values[0])
                lst_lon.append(df_codes[df_codes["name"]==i['country']['country_name']]['longitude'].values[0])
        
        data['country_name'] = lst_country 
        data['total_cases'] = lst_total_cases
        data['total_deaths'] = lst_total_deaths
        data['total_recovered'] = lst_total_recovered
        data['lat'] = lst_lat
        data['long'] = lst_lon

        df_count = pd.DataFrame(data)
        for _,value in df_count.iterrows():
            text_lst.append(f"Country: {value['country_name']}\n Total Case:{value['total_cases']}\n Total Death:{value['total_deaths']}\n Total Recovered:{value['total_recovered']}")
        df_count['text'] = text_lst
        
        return df_count
    

    def run(self,dispatcher,tracker,domain):
        country_lst =[]
        covid_res = []
        msg = "Fetching global pandamic information might take some time"
        dispatcher.utter_message(msg)
        try:
            entities = tracker.latest_message['entities']

            for ent in entities:
                if ent['entity'] in ['GPE']:
                    country_lst.append(ent['value'])
            country_lst = list(set(country_lst))
            if country_lst:
                covid_res = self.country_api(country_lst=country_lst)
                covid_df = self.get_res_df(res=covid_res)
                if len(covid_df['text'].values)>1:
                    covid_count = '\n'.join(covid_df['text'].values)
                else:
                    covid_count = covid_df['text'].values[0]
                dispatcher.utter_message(covid_count)
            else:
                dispatcher.utter_message("This is todays latest COVID data please check https://covidworldwidemap.herokuapp.com/insight")
        except:
            dispatcher.utter_message("Sorry unable to fetch the covid details of the country")
        return []

#to handle FAQ/small talk questions
class Action_FAQ(Action):
    def name(self):
        return "action_faq"
    def run(self,dispatcher,tracker,domain):
        try:
            intent_name = tracker.latest_message['intent'].get('name')
            if FORM_NAME:
                return [FollowupAction(FORM_NAME)]
            else:
                res = res_df.loc[res_df['Intent']==intent_name].iloc[:,1]
                dispatcher.utter_message(res.item())
                if intent_name == 'prevention':
                    dispatcher.utter_message(template='utter_cheer_up')
        except:
            dispatcher.utter_message("Something went wrong!")
        return []


#to fetch user information
class Fetch_INFO(Action):
    def name(self):
        return "fetch_info"

    #to send email notification    
    @staticmethod
    def send_mail(to_addr):
        fromaddr = params.FROM_ADDR
        toaddr = to_addr
        msg = MIMEMultipart() 
        msg['From'] = fromaddr  
        msg['To'] = toaddr 
        msg['Subject'] = "COVID-19 Prevention"
        res = res_df.loc[res_df['Intent']=='prevention'].iloc[:,1]
        body = res.item() + "This is todays latest COVID data please check https://covidworldwidemap.herokuapp.com/insight"
        msg.attach(MIMEText(body, 'plain'))  
        filename = "covid_prevention.png"
        attachment = open("covid_prevention.png", "rb")  
        p = MIMEBase('application', 'octet-stream') 
        p.set_payload((attachment).read()) 
        encoders.encode_base64(p) 
        p.add_header('Content-Disposition', "attachment; filename= %s" % filename) 
        msg.attach(p) 
        s = smtplib.SMTP('smtp.gmail.com', 587) 
        s.starttls() 
        s.login(fromaddr, params.FROM_PASS) 
        text = msg.as_string() 
        s.sendmail(fromaddr, toaddr, text) 
        s.quit() 

    #inserting user data to DB
    @staticmethod
    def db_user_insert(user_dict):
        try:
            rasaclient = pymongo.MongoClient(params.MONGO_URL)
            rasadb = rasaclient[params.MONGO_DB]
            rasacol = rasadb[params.MONGO_USER]
            rasacol.insert_one(user_dict)  
        except Exception as e:
            print("Error occured during insertion", e)

    def run(self,dispatcher,tracker,domain):
        try:
            entity_name = None
            entity_val = None
            user_dict = dict()
            ent_nm = tracker.latest_message['entities']
            user_nm = tracker.get_slot('person')
            user_st = tracker.get_slot('state')
            phone = tracker.get_slot('phone')
            pin = tracker.get_slot('pin')
            email = tracker.get_slot('email')
            user_dict['name'],user_dict['contact'],user_dict['pin'],user_dict['email'] = user_nm,phone,pin,email

            if ent_nm:
                entity_name = ent_nm[0]['entity']
                entity_val = ent_nm[0]['value']
            #validating user information
            if user_nm and phone and pin and email:
                dispatcher.utter_message(f"Hi {user_nm.title()} 🙋‍♂️. Thank you for using COVID-19 helpline. We have send across a mail Regarding COVID safety tips and daily COVID reports.Stay safe :)")
                if tracker.get_slot('country') != 's':
                    self.db_user_insert(user_dict)  
                    #self.send_mail(email)
                return [SlotSet('country','s')]
            else:
                if entity_name == 'PERSON' and not user_nm:
                    dispatcher.utter_message(f"Hi {entity_val.title()} 🙋‍♂️.Please enter your contact number 📱")
                    return [SlotSet('state',entity_val),SlotSet('person',entity_val)]

                elif entity_name == 'phone' or (user_nm and not phone):
                    if not phone:
                        dispatcher.utter_message(f"contact number 📱 doesn't look correct !")
                        dispatcher.utter_message(f"Hi {user_nm.title()} 🙋‍♂️.Please enter your contact number 📱")
                        return []
                    else:
                        dispatcher.utter_message(f"Please enter PIN CODE")
                        return SlotSet('phone',entity_val)

                elif entity_name == 'pin' or (phone and not pin):
                    if not pin:
                        dispatcher.utter_message(f"not able to process the pin code !")
                        dispatcher.utter_message(f"Please enter your PIN CODE")
                        return []
                    else:
                        dispatcher.utter_message(f"Please enter Email address")
                        return SlotSet('pin',entity_val)    
                elif entity_name == 'email' or (pin and not email):
                    if not email:
                        dispatcher.utter_message(f"Unable to process the email id!")
                        dispatcher.utter_message(f"please enter your Email id")
                        return []
                    else:
                        return [SlotSet('email',entity_val),FollowupAction('fetch_info')]
                else:
                    if not user_nm:
                        dispatcher.utter_message("Please enter your Full name")
                    else:
                        dispatcher.utter_message("something went wrong.Let try again")
                        ent_nm = {}
                        return [FollowupAction('fetch_info')]


        except:
            dispatcher.utter_message("I am sorry i was not able to understand you correctly")
        return []

