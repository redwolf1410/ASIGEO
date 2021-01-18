from datetime import datetime
import threading
import time
from socket import create_connection, gethostbyname, error
from UliEngineering.Physics.RTD import pt1000_temperature
import kivy
import json
import os
from kivy.uix.screenmanager import ScreenManager

import numpy as np
import math

kivy.require("1.9.1")
from kivy.config import Config

Config.set('kivy', 'keyboard_mode', 'systemanddock')

Config.set("graphics", "width", "650")
Config.set("graphics", "height", "390")
Config.write()
from LogicaUna import LogicaZona, LogicaZonaDirecta
from kivy.app import App
from kivy.lang import Builder


import Adafruit_DHT
from MCP3208 import MCP3208
# Software SPI configuration:
CLK = 11
MISO = 9
MOSI = 10
CS = 8

mcp = MCP3208(clk=CLK, cs=CS, miso=MISO, mosi=MOSI)


def comprobarConexion():
    try:
        gethostbyname('google.com')
        cnx = create_connection(('google.com', 80), 1)
        conexion = True
    except:
        conexion = False

    return conexion


class Main(ScreenManager):
    def dummy(self):
        pass

    def cambia_from(self, num):
        des = self.ids.desde.text
        desde = int(des) + num
        if 23 >= desde >= 0:
            self.ids.desde.text = str(desde)

    def cambia_to(self, num):
        has = self.ids.hasta.text
        hasta = int(has) + num
        if hasta != 24 and hasta != 1:
            self.ids.hasta.text = str(hasta)

    def cambiar_consigna(self, num, zona):
        if zona == 1:
            consigna = self.ids.consigna1.text
        elif zona == 2:
            consigna = self.ids.consigna2.text

        else:
            consigna = self.ids.consigna3.text

        cons_sp1 = consigna.split(']')
        cons_sp2 = cons_sp1[1].split('[')
        consigna = int(cons_sp2[0]) + num
        text = cons_sp1[0] + ']' + str(consigna) + '[' + cons_sp2[1] + ']'

        if zona == 1:
            self.ids.consigna1.text = text
        elif zona == 2:
            self.ids.consigna2.text = text
        else:
            self.ids.consigna3.text = text


def from_level_to_temp(level):
    error = False
    volt = level * 3.3 / 3900
    r = (1000 * volt) / (3.3 - volt)
    r1 = 100000 * r / (100000 - r)
    temp = pt1000_temperature(r1)
    if np.isnan(temp) or -100 < temp > 100:
        error = True
    return temp, error


def from_level_to_temp_ntc(beta, r25, level):
    volt = level * 3.3 / 3900
    r = (10000 * volt) / (3.3 - volt)
    r1 = 100000 * r / (100000 - r)
    error = False
    temp = -30
    if r1 > 0:
        temp = beta / (math.log(r1 / r25) + beta / 298) - 273
    else:
        error = True

    if temp < -17:
        error = True
    return temp, error


class MainApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # SEGURIDADES
        with open('json_f/seguridades.json', 'r') as file:
            seguridades = json.load(file)

        self.act_seguridades = 0



        self.dict_dias = {"Lunes": 0, "Martes": 1, "Miercoles": 2, "Jueves": 3, "Viernes": 4, "Sabado": 5, "Domingo": 6,
                          "Laborables": [0, 1, 2, 3, 4], "Fin de semana": [5, 6], "Todos": [0, 1, 2, 3, 4, 5, 6], }
        self.colores = {0: [0.99, .0, .0], 1: [1, .82, .0], 2: [.0, 1., 0.62]}
        self.t_ext = 35
        self.act_screen = "menu"
        self.chanels = [0, 0, 0, 0, 0, 0, 0, 0]
        self.ch_errors = [False, False, False, False, False, False, False, False]
        self.error = False
        self.t_amb = [20, 20, 20]
        self.etiqprinc = ""
        self.t_suelo = [25, 25]

        self.t_agua = [25, 25]
        self.scheduler = np.load("json_f/scheduler.npy")
        with open("json_f/modo.json") as f:
            modo = json.load(f)
            self.modo = modo['modo']
            print("El modo con el que se ha inicializado es " + self.modo)
        if self.modo == "invierno":
            self.etiqprinc = '[b][color=FF1700] MODO CALEFACCION [/color][/b]'

        elif self.modo == "verano":
            self.etiqprinc = '[b][color=5FE5B5] MODO REFRIGERACION [/color][/b]'

        else:
            self.etiqprinc = '[b][color=A49B0F] APAGADO [/color][/b]'

        with open("json_f/pantalla1.json") as f:
            pant = json.load(f)
            cons1 = pant['consigna']

        with open("json_f/pantalla2.json") as f:
            pant = json.load(f)
            cons2 = pant['consigna']

        with open("json_f/pantalla3.json") as f:
            pant = json.load(f)
            cons3 = pant['consigna']
        self.consignas = [cons1, cons2, cons3]
        with open("json_f/consignas.json") as f:
            pant = json.load(f)
            self.reducido_inv = pant['reducido_inv']
            self.reducido_ver = pant['reducido_ver']
            self.apagado_inv = pant['apagado_inv']
            self.apagado_ver = pant['apagado_ver']

        self.zona = 0


        with open("json_f/ajustes.json") as f:
            ajustes = json.load(f)
            bombas = ajustes['bombas']
            self.bombas = [bool(bombas[0]), bool(bombas[1])]
            self.curvas = ajustes['curvas']
            self.pt1000 = ajustes['pt1000']

        self.comfort = [0, 0]
        with open("json_f/states.json") as f:
            self.states = json.load(f)
        with open("json_f/states_sondas.json") as f:
            self.states_sondas = json.load(f)

        with open("json_f/estado_bombas.json") as f:
            self.estado_bombas = json.load(f)
        with open("json_f/estado_curvas.json") as f:
            self.estado_curvas = json.load(f)

        self.ajustes = True

        self.logicas = [LogicaZona(1), LogicaZona(2)]
        self.zona_directa = LogicaZonaDirecta(rele=7)

        self.mutex = threading.Semaphore(1)
        self.mutex_sec = threading.Semaphore(1)
        self.mutex_init = threading.Semaphore(0)


        thread1 = threading.Thread(target=self.main, args=[1])
        thread1.start()

        thread2 = threading.Thread(target=self.main, args=[2])
        thread2.start()

        thread3 = threading.Thread(target=self.main_directa, args=[3])
        thread3.start()

        th_read = threading.Thread(target=self.lectura_sondas)
        th_read.start()
    def backzone(self):
        if self.zona == 0:
            self.root.current = "menu1"
        elif self.zona == 1:
            self.root.current = "menu2"
    def camzona(self,zona):
        self.zona = zona

    def set_secvalue(self):

        modo = self.root.ids.seg_modo.text
        zona = self.root.ids.seg_zonas.text
        sec = self.root.ids.seguridades.text
        print(modo, zona, sec)
        seguridad = self.get_seguridad(modo, zona, sec)

        print(seguridad)

        with open('json_f/seguridades.json') as f:
            seguridades = json.load(f)
            self.root.ids.valor_actual.text = str(seguridades[seguridad])
            self.root.ids.nuevo_valor.text = ''

    def cambiar_titulos(self, zona):
        if zona == 1:
            self.root.ids.title_1.text = self.root.ids.new_title1.text
            self.root.ids.new_title1.text = ''
        elif zona == 2:
            self.root.ids.title_2.text = self.root.ids.new_title2.text
            self.root.ids.new_title2.text = ''
        elif zona == 3:
            self.root.ids.title_3.text = self.root.ids.new_title3.text
            self.root.ids.new_title3.text = ''

    def rm_label(self):
        self.root.ids.valor_actual.text = ''
        self.root.ids.nuevo_valor.text = ''

    def reset_fabrica(self):
        os.system('sh reset_parametros.sh')

    def set_seguridad(self):
        modo = self.root.ids.seg_modo.text
        zona = self.root.ids.seg_zonas.text
        sec = self.root.ids.seguridades.text
        n_valor = self.root.ids.nuevo_valor.text
        try:
            nvalor = int(n_valor)
            seguridad = self.get_seguridad(modo, zona, sec)
            print(seguridad)
            with open('json_f/seguridades.json', 'r+') as f:
                seguridades = json.load(f)
            with open('json_f/seguridades.json', 'w') as f:

                if seguridad != 0:
                    f.seek(0)
                    self.root.ids.valor_actual.text = str(nvalor)
                    seguridades[seguridad] = nvalor
                    json.dump(seguridades, f, indent=4)
                    self.root.ids.sec_err.text = ""
                else:
                    self.root.ids.sec_err.text = "Seguridad no seleccionada"


        except:
            self.root.ids.sec_err.text = "Valores numéricos erroneos"

    def get_seguridad(self, modo, zona, sec):
        if modo == 'Verano':
            pre = 'ver'
        elif modo == 'Invierno':
            pre = 'inv'
        elif modo == 'Antihielo':
            pre = 'ant'

        if sec == 'T min Suelo':
            mid = '_tmin_suelo'
        elif sec == 'T max Suelo':
            mid = '_tmax_suelo'
        elif sec == 'T min Agua':
            mid = '_tmin_agua'
        elif sec == 'T max Agua':
            mid = '_tmax_agua'
        elif sec == 'T min Exterior':
            seguridad = pre + '_tmin_ext'
        else:
            return 0

        if zona != 'Comunes':
            pos = zona[-1]
            seguridad = pre + mid + pos

        return seguridad

    def readSensors(self):
        #print('Leyendo sensores')
        error = False
        for i in range(0, 8):
            lev = mcp.read(i)

            if self.pt1000[i]:
                ch, err = from_level_to_temp(lev)
            else:
                if i == 3 or i == 6:
                    ch, err = from_level_to_temp_ntc(3976, 10000, lev)
                else:
                    ch, err = from_level_to_temp_ntc(3435, 10000, lev)

            if err:
                self.ch_errors[i] = True
                error = True
            else:
                self.ch_errors[i] = False

            self.chanels[i] = ch
        self.error = error

        print(self.chanels)

    def borrar_scheduler(self):
        self.scheduler[:, :, :] = 0
        np.save("json_f/scheduler.npy",self.scheduler)

    def cambiar_modo(self, modo):
        self.modo = modo
        if modo == 'invierno':
            self.states['winter'] = 'down'
            self.states['summer'] = 'normal'
            self.states['noice'] = 'normal'
            color = '[color=00E4FF]'
            self.root.ids.modo0.text = '[b][color=FF1700] MODO CALEFACCION [/color][/b]'
        if modo == 'verano':
            self.states['winter'] = 'normal'
            self.states['summer'] = 'down'
            self.states['noice'] = 'normal'
            color = '[color=FF8700]'
            self.root.ids.modo0.text = '[b][color=54EDE1] MODO REFRIGERACION [/color][/b]'
        if modo == 'antihielo':
            self.states['winter'] = 'normal'
            self.states['summer'] = 'normal'
            self.states['noice'] = 'down'
            color = '[color=EF4A4A]'
            self.root.ids.modo0.text = '[b][color=F1F132] MODO ANTIHIELO [/color][/b]'

        self.root.ids.modo1.text = color + modo.capitalize() + '[/color]'
        self.root.ids.modo2.text = color + modo.capitalize() + '[/color]'
        self.root.ids.modo3.text = color + modo.capitalize() + '[/color]'
        data = {
            'modo': self.modo
        }
        with open('json_f/modo.json', 'w') as file:
            json.dump(data, file, indent=4)

        with open('json_f/states.json', 'w') as file:
            json.dump(self.states, file,indent=4)

    def modo_comfort(self, comfort, zona):
        self.comfort[zona] = comfort

    def copiar_sched(self):
        dia = self.root.ids.dias.text
        dia = self.dict_dias[dia]
        zona = self.zona
        dia_copiar = self.root.ids.copiar_a.text
        dia_copiar = self.dict_dias[dia_copiar]

        dia_sched = self.scheduler[zona, dia, :]
        self.scheduler[zona, dia_copiar, :] = dia_sched
        np.save("json_f/scheduler.npy", self.scheduler)

    def reset_sched(self):
        self.scheduler = np.zeros((2, 7, 24))
        self.root.ids.dias.text = 'Lunes'
        self.cambiar_dia()
        np.save("json_f/scheduler.npy", self.scheduler)

    def cambiar_dia(self):
        dia = self.root.ids.dias.text
        dia = self.dict_dias[dia]
        dia_sched = self.scheduler[self.zona, dia, :]

        h1 = self.colores[int(dia_sched[0])]
        self.root.ids.h00.background_color = self.colores[int(dia_sched[0])]
        self.root.ids.h01.background_color = self.colores[int(dia_sched[1])]
        self.root.ids.h02.background_color = self.colores[int(dia_sched[2])]
        self.root.ids.h03.background_color = self.colores[int(dia_sched[3])]
        self.root.ids.h04.background_color = self.colores[int(dia_sched[4])]
        self.root.ids.h05.background_color = self.colores[int(dia_sched[5])]
        self.root.ids.h06.background_color = self.colores[int(dia_sched[6])]
        self.root.ids.h07.background_color = self.colores[int(dia_sched[7])]
        self.root.ids.h08.background_color = self.colores[int(dia_sched[8])]
        self.root.ids.h09.background_color = self.colores[int(dia_sched[9])]
        self.root.ids.h10.background_color = self.colores[int(dia_sched[10])]
        self.root.ids.h11.background_color = self.colores[int(dia_sched[11])]
        self.root.ids.h12.background_color = self.colores[int(dia_sched[12])]
        self.root.ids.h13.background_color = self.colores[int(dia_sched[13])]
        self.root.ids.h14.background_color = self.colores[int(dia_sched[14])]
        self.root.ids.h15.background_color = self.colores[int(dia_sched[15])]
        self.root.ids.h16.background_color = self.colores[int(dia_sched[16])]
        self.root.ids.h17.background_color = self.colores[int(dia_sched[17])]
        self.root.ids.h18.background_color = self.colores[int(dia_sched[18])]
        self.root.ids.h19.background_color = self.colores[int(dia_sched[19])]
        self.root.ids.h20.background_color = self.colores[int(dia_sched[20])]
        self.root.ids.h21.background_color = self.colores[int(dia_sched[21])]
        self.root.ids.h22.background_color = self.colores[int(dia_sched[22])]
        self.root.ids.h23.background_color = self.colores[int(dia_sched[23])]

    def set_sched_hora(self, hora, dia, valor):
        dia_sched = self.dict_dias[dia]
        self.scheduler[self.zona, dia_sched, hora] = valor
        np.save("json_f/scheduler.npy", self.scheduler)

    def dummy(self):
        pass

    def modo_curva(self, curva, zona):
        self.curvas[zona] = curva
        with open("json_f/ajustes.json", 'r+') as f:
            ajustes = json.load(f)
            aj_curva = ajustes['curvas']
            aj_curva[zona] = int(curva)
            ajustes['curvas'] = aj_curva
            f.seek(0)
            json.dump(ajustes, f,indent=4)

        if curva == 0:
            self.estado_curvas[zona]["b1"] = "down"
            self.estado_curvas[zona]["b2"] = "normal"
            self.estado_curvas[zona]["b3"] = "normal"
        elif curva == 1:
            self.estado_curvas[zona]["b1"] = "normal"
            self.estado_curvas[zona]["b2"] = "down"
            self.estado_curvas[zona]["b3"] = "normal"
        elif curva == 2:
            self.estado_curvas[zona]["b1"] = "normal"
            self.estado_curvas[zona]["b2"] = "normal"
            self.estado_curvas[zona]["b3"] = "down"
        with open("json_f/estado_bombas.json", "w") as f:
            json.dump(self.estado_bombas, f, indent=4)

    def modo_bomba(self, zona, modo):
        self.bombas[zona] = modo
        with open("json_f/ajustes.json", 'r+') as f:
            ajustes = json.load(f)
            aj_bomba = ajustes['bombas']
            aj_bomba[zona] = int(modo)
            ajustes['bombas'] = aj_bomba
            f.seek(0)
            json.dump(ajustes, f,indent=4)
        if modo:
            self.estado_bombas[zona]["b1"] = "normal"
            self.estado_bombas[zona]["b2"] = "down"
            try:

                if zona==0: self.root.ids.mod_bomb_z1.text = "[b] MODO ECO [/b]"
                elif zona==1: self.root.ids.mod_bomb_z2.text = "[b] MODO ECO [/b]"
            except:
                print(Exception)
        else:
            self.estado_bombas[zona]["b1"] = "down"
            self.estado_bombas[zona]["b2"] = "normal"
            try:

                if zona==0: self.root.ids.mod_bomb_z1.text = "[b] AUTO ON [/b]"
                elif zona==1: self.root.ids.mod_bomb_z2.text = "[b] AUTO ON [/b]"
            except:
                print(Exception)
        with open("json_f/estado_bombas.json", "w") as f:
            json.dump(self.estado_bombas, f, indent=4)


    def cambia_sonda(self, sonda, num):
        self.pt1000[num] = sonda
        with open("json_f/ajustes.json", 'r+') as f:
            ajustes = json.load(f)
            ajustes['pt1000'] = self.pt1000
            f.seek(0)
            json.dump(ajustes, f,indent=4)

        if sonda == 0:
            self.states_sondas[num]["b1"] = "normal"
            self.states_sondas[num]["b2"] = "down"
        else:
            self.states_sondas[num]["b1"] = "down"
            self.states_sondas[num]["b2"] = "normal"
        with open("json_f/states_sondas.json", "w") as f:
            json.dump(self.states_sondas, f, indent=4)
    def lock(self):
        self.ajustes = True
        self.next_screen('menu')

    def do_login(self, user, password):
        with open("json_f/user.json") as f:
            login = json.load(f)
        if user == login['user'] and password == login['password']:
            self.root.current = "ajustes_admin"
            self.root.ids.user.text = ''
            self.root.ids.passw.text = ''

        else:
            self.root.ids.user.text = ''
            self.root.ids.passw.text = ''

    def lectura_sondas(self):
        contador = 0
        arr_tamb1 = np.zeros(5)
        arr_tamb2 = np.zeros(5)
        arr_text = np.zeros(5)
        arr_tsuelo1 = np.zeros(5)
        arr_tsuelo2 = np.zeros(5)

        while True:
            self.readSensors()
            arr_tamb1 = np.roll(arr_tamb1, 1)
            arr_tamb2 = np.roll(arr_tamb2, 1)
            arr_text = np.roll(arr_text, 1)
            arr_tsuelo1 = np.roll(arr_tsuelo1, 1)
            arr_tsuelo2 = np.roll(arr_tsuelo2, 1)

            arr_text[0] = self.chanels[0]
            arr_tsuelo1[0] = self.chanels[1]
            arr_tsuelo2[0] = self.chanels[4]

            arr_tamb1[0] = self.chanels[3]
            arr_tamb2[0] = self.chanels[6]

            if contador == 5:
                self.mutex.acquire()
                self.t_agua[0] = round(self.chanels[2], 1)
                self.t_agua[1] = round(self.chanels[2], 1)  # Esto hay que cambiarlo luego, SOLO TEST
                self.t_ext = round(np.mean(arr_text), 1)
                self.t_suelo[0] = round(np.mean(arr_tsuelo1), 1)
                self.t_amb[0] = round(np.mean(arr_tamb1), 1)
                self.t_suelo[1] = round(np.mean(arr_tsuelo1), 1)  # SOLO TEST
                self.t_amb[1] = round(np.mean(arr_tamb2), 1)
                self.t_amb[2] = round(self.chanels[7], 1)

                self.mutex.release()
                try:
                    self.actualizar_labels()
                    """if comprobarConexion():
                        self.root.ids.conexion.source = "data/internet.png"
                    else:
                        self.root.ids.conexion.source = "data/nointernet.png"""
                    contador = 0

                except:
                    print("Error de carga")
            time.sleep(1)
            contador += 1

    def main_directa(self, zona):
        zona = zona - 1
        while True:
            self.mutex.acquire()
            self.zona_directa.t_amb = self.t_amb[zona]
            self.zona_directa.consigna = self.consignas[zona]
            self.mutex.release()
            funcionando = self.zona_directa.logica(self.modo)
            time.sleep(5)
            try:
                if funcionando:
                    self.root.ids.abriendo3.text = 'Encendido'
                else:
                    self.root.ids.abriendo3.text = 'Apagado'

            except:
                print("KV no inicializado")



    def main(self, zona):
        zona = zona - 1
        while True:
            try:

                while True:
                    ahora = datetime.now()
                    hora = ahora.hour
                    hour = "{:0>2d}".format(ahora.hour)
                    min = "{:0>2d}".format(ahora.minute)
                    day = "{:0>2d}".format(ahora.day)
                    mth = "{:0>2d}".format(ahora.month)
                    year = str(ahora.year)
                    try:
                        self.root.ids.hora.text = hour +':' + min
                        self.root.ids.fecha.text = day + '/' + mth + '/' + year
                    except:
                        print(Exception)


                    dia = datetime.weekday(ahora)
                    sched = self.scheduler[zona,dia, hora]

                    if self.act_seguridades == 1:
                        self.mutex_sec.acquire()
                        self.logicas[zona].act_seguridades()
                        self.act_seguridades = 0
                        self.mutex_sec.release()
                    self.mutex.acquire()
                    self.logicas[zona].sonda_exterior = self.t_ext
                    self.logicas[zona].sonda_ambiente = self.t_amb[zona]
                    self.logicas[zona].sonda_agua = self.t_agua[zona]
                    self.logicas[zona].sonda_suelo = self.t_suelo[zona]
                    self.logicas[zona].modo_bomba = self.bombas[zona]
                    self.logicas[zona].modo_curva = self.curvas[zona]
                    print("El modo es " + self.modo)

                    if sched == 0:



                        if self.modo == 'invierno':
                            self.logicas[zona].consigna = self.consignas[zona]
                        elif self.modo == 'verano':
                            self.logicas[zona].consigna = self.consignas[zona]
                    elif sched == 1:
                        if self.modo == 'invierno':
                            self.logicas[zona].consigna = self.reducido_inv[zona]
                        elif self.modo == 'verano':
                            self.logicas[zona].consigna = self.reducido_ver[zona]

                    elif sched == 2:
                        if self.modo == 'invierno':
                            self.logicas[zona].consigna = self.apagado_inv[zona]
                        elif self.modo == 'verano':
                            self.logicas[zona].consigna = self.apagado_ver[zona]

                    self.etiquetas_mod(sched, zona)
                    self.mutex.release()
                    if False: #self.error:#Esto cuando sepamos que va bien descomentar
                        self.logicas[zona].seguridad()
                        time.sleep(5)
                    else:
                        func = self.logicas[zona].logica(self.modo)
                        print("zona " + str(zona),"funcionando" + str(func))


                    if zona == 0:
                        if func == 1 or func == 2:
                            self.root.ids.abriendo1.text = 'Abriendo'
                            self.root.ids.est_reg_z1_p0.text = 'Abriendo'
                        elif func == 3:
                            self.root.ids.abriendo1.text = 'Cerrando'
                            self.root.ids.est_reg_z1_p0.text = 'Cerrando'
                        else:
                            self.root.ids.abriendo1.text = 'T Correcta'
                            self.root.ids.est_reg_z1_p0.text = 'T Correcta'
                    elif zona == 1:
                        if func == 1 or func == 2:
                            self.root.ids.abriendo2.text = 'Abriendo'
                            self.root.ids.est_reg_z2_p0.text = 'Abriendo'
                        elif func == 3:
                            self.root.ids.abriendo2.text = 'Cerrando'
                            self.root.ids.est_reg_z2_p0.text = 'Cerrando'
                        else:
                            self.root.ids.abriendo2.text = 'T Correcta'
                            self.root.ids.est_reg_z2_p0.text = 'T Correcta'



            finally:
                print("Error")

    def cambiar_consigna(self, num, zona):

        if self.consignas[zona] + num >= 10:
            self.consignas[zona] = self.consignas[zona] + num

        if zona == 0:
            self.root.ids.cons_z1_inv_conf.text = str(self.consignas[zona])
            self.root.ids.cons_z1_ver_conf.text = str(self.consignas[zona])
        elif zona == 1:
            self.root.ids.cons_z2_inv_conf.text = str(self.consignas[zona])
            self.root.ids.cons_z2_ver_conf.text = str(self.consignas[zona])

        else:
            self.root.ids.consigna3.text = '[color=1ED760]' + str(self.consignas[zona]) + '[/color]'

        with open("json_f/pantalla" + str(zona + 1) + ".json", 'r+') as f:
            pant = json.load(f)
            pant['consigna'] = self.consignas[zona]
            f.seek(0)
            json.dump(pant, f,indent=4)

    def cambiar_cons_reducido(self, num, zona, modo):
        zona = zona - 1
        if zona == 0:
            if modo == 'inv':
                self.reducido_inv[zona] = self.reducido_inv[zona] + num
                self.root.ids.cons_z1_inv_red.text = str(self.reducido_inv[zona])
            else:
                self.reducido_ver[zona] = self.reducido_ver[zona] + num
                self.root.ids.cons_z1_ver_red.text = str(self.reducido_ver[zona])
        elif zona == 1:
            if modo == 'inv':
                self.reducido_inv[zona] = self.reducido_inv[zona] + num
                self.root.ids.cons_z2_inv_red.text = str(self.reducido_inv[zona])

            else:
                self.reducido_ver[zona] = self.reducido_ver[zona] + num
                self.root.ids.cons_z2_ver_red.text = str(self.reducido_ver[zona])

    def cambiar_cons_apagado(self, num, zona, modo):
        zona = zona - 1
        if zona == 0:
            if modo == 'inv':
                self.apagado_inv[zona] = self.apagado_inv[zona] + num
                self.root.ids.cons_z1_inv_apa.text = str(self.apagado_inv[zona])
            else:
                self.apagado_ver[zona] = self.apagado_ver[zona] + num
                self.root.ids.cons_z1_ver_apa.text = str(self.apagado_ver[zona])
        elif zona == 1:
            if modo == 'inv':
                self.apagado_inv[zona] = self.apagado_inv[zona] + num
                self.root.ids.cons_z2_inv_apa.text = str(self.apagado_inv[zona])

            else:
                self.apagado_inv[zona] = self.apagado_inv[zona] + num
                self.root.ids.cons_z2_ver_apa.text = str(self.apagado_ver[zona])

    def build(self):
        self.root = Builder.load_file('kv/main.kv')

    def actualizar_labels(self):
        if not self.ch_errors[0]:
            self.root.ids.t_ext0.text ='[b]T EXTERIOR:' + '    ' + '[color=006CFF]' + str(self.t_ext) + ' [/color][/b]'
            self.root.ids.t_ext1.text = str(self.t_ext)
            self.root.ids.t_ext2.text = str(self.t_ext)
            self.root.ids.t_ext3.text = str(self.t_ext)
            self.root.ids.t_exterior.text = str(self.t_ext)
        else:
            self.root.ids.t_ext0.text = '[b]T EXTERIOR:' + '    ' + '[color=BE1515]' + 'ERROR' + ' [/color][/b]'
            self.root.ids.t_ext1.text = '[color=F14108] Error [/color]'
            self.root.ids.t_ext2.text = '[color=F14108] Error [/color]'
            self.root.ids.t_ext3.text = '[color=F14108] Error [/color]'
            self.root.ids.t_exterior.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[1]:

            self.root.ids.t_suelo_z1.text = str(self.t_suelo[0])
        else:

            self.root.ids.t_suelo_z1.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[2]:

            self.root.ids.t_agua_z1.text = str(self.t_agua[0])
            self.root.ids.t_agua_z1_p0.text = '[b]'+str(self.t_agua[0]) + 'ºC [/b]'
        else:

            self.root.ids.t_agua_z1.text = '[color=F14108] Error [/color]'
            self.root.ids.t_agua_z1_p0.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[3]:
            self.root.ids.t_amb1.text = str(self.t_amb[0])
            self.root.ids.t_amb_z1.text = str(self.t_amb[0])
            self.root.ids.t_amb_z1_p0.text = '[b]' + str(self.t_amb[0]) + 'ºC[/b]'
        else:
            self.root.ids.t_amb1.text = '[color=F14108] Error [/color]'
            self.root.ids.t_amb_z1.text = '[color=F14108] Error [/color]'
            self.root.ids.t_amb_z1_p0.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[4]:

            self.root.ids.t_suelo_z2.text = str(self.t_suelo[1])
        else:

            self.root.ids.t_suelo_z2.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[5]:

            self.root.ids.t_agua_z2.text = str(self.t_agua[1])
            self.root.ids.t_agua_z2_p0.text ='[b]' + str(self.t_agua[1]) + 'ºC [/b]'
        else:

            self.root.ids.t_agua_z2.text = '[color=F14108] Error [/color]'
            self.root.ids.t_agua_z2_p0.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[6]:
            self.root.ids.t_amb2.text = str(self.t_amb[1])
            self.root.ids.t_amb_z2.text = str(self.t_amb[1])
            self.root.ids.t_amb_z2_p0.text = '[b]' + str(self.t_amb[1])+'ºC [/b]'
        else:
            self.root.ids.t_amb2.text = '[color=F14108] Error [/color]'
            self.root.ids.t_amb_z2.text = '[color=F14108] Error [/color]'
            self.root.ids.t_amb_z2_p0.text = '[color=F14108] Error [/color]'

        if not self.ch_errors[7]:
            self.root.ids.t_amb3.text = str(self.t_amb[2])
            self.root.ids.t_amb_z3.text = str(self.t_amb[2])
            self.root.ids.t_amb_z3_p0.text = '[b]' + str(self.t_amb[2]) +'ºC [/b]'

        else:
            self.root.ids.t_amb3.text = '[color=F14108] Error [/color]'
            self.root.ids.t_amb_z3.text = '[color=F14108] Error [/color]'
            self.root.ids.t_amb_z3_p0.text = '[color=F14108] Error [/color]'

    def etiquetas_mod(self, sched, zona):
        print(self.consignas[zona])
        if zona == 0:
            try:
                self.root.ids.t_des_z1_p0.text = str(self.consignas[zona])
            except:
                print("Error kivy zona 1 consignas p0")
            try:
                if sched == 0:
                    self.root.ids.modo_z1.text = 'CONFORT'

                elif sched == 1:
                    self.root.ids.modo_z1.text = 'REDUCIDO'
                else:
                    self.root.ids.modo_z1.text = 'APAGADO'
            except:
                print("Error kivy zona 1 modo p0")

        elif zona == 1:
            try:
                self.root.ids.t_des_z2_p0.text = str(self.consignas[zona])
                self.root.ids.t_des_z3_p0.text = str(self.consignas[2])
            except:print("Error kivy zona 2 consignas p0")

            try:
                if sched == 0:
                    self.root.ids.modo_z2.text = 'CONFORT'
                elif sched == 1:
                    self.root.ids.modo_z2.text = 'REDUCIDO'
                else:
                    self.root.ids.modo_z2.text = 'APAGADO'
            except:print("Error kivy confort p0")







if __name__ == '__main__':
    MainApp().run()
