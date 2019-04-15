import gym
from gym import spaces
import numpy
import pandas
from datetime import datetime
from MergedDataStructure import MergedDataStructure
import Callback


class SpEnv(gym.Env):
    
    continuous = False

    def __init__(self, minLimit=None, maxLimit=None, operationCost = 0, observationWindow = 40, ensamble = None, callback = None, columnName = "iteration-1"):
        self.episodio=1

        spTimeserie = pandas.read_csv('./dataset/sp500Hour.csv')[minLimit:maxLimit] # opening the dataset
        Date = spTimeserie.ix[:, 'Date'].tolist()
        Time = spTimeserie.ix[:, 'Time'].tolist()
        Open = spTimeserie.ix[:, 'Open'].tolist()
        High = spTimeserie.ix[:, 'High'].tolist()
        Low = spTimeserie.ix[:, 'Low'].tolist()
        Close = spTimeserie.ix[:, 'Close'].tolist()
        Volume = spTimeserie.ix[:, 'Volume'].tolist()

        self.weekData = MergedDataStructure(delta=8,filename="./dataset/sp500Week.csv")# this DS allows me to obtain previous historical data with different resolution
        self.dayData = MergedDataStructure(delta=20,filename="./dataset/sp500Day.csv")#  with low computational complexity
        
        
        self.output=False

        if(ensamble is not None): # managing the ensamble output (maybe in the wrong way)
            self.output=True
            self.ensamble=ensamble
            self.columnName = columnName
            self.ensamble[self.columnName]=0

        self.low = numpy.array([-numpy.inf])
        self.high = numpy.array([+numpy.inf])
        self.action_space = spaces.Discrete(3) # the action space is just 0,1,2 which means hold,long,short
        self.observation_space = spaces.Box(self.low, self.high, dtype=numpy.float32)


        self.history=[]
        self.observationWindow = observationWindow
        self.currentObservation = observationWindow
        #print(self.currentObservation)
        self.operationCost=operationCost
        self.done = False
        self.limit = len(Open)
        for i in range(0,self.limit): # organizing the dataset as a list of dictionaries
            self.history.append({'Date' : Date[i],'Time' : Time[i], 'Open': Open[i], 'High': High[i], 'Low': Low[i], 'Close': Close[i], 'Volume': Volume[i] })
        
        self.nextObservation=0
        # print(self.currentObservation)
        while(self.history[self.currentObservation]['Date']==self.history[(self.currentObservation+self.nextObservation)%self.limit]['Date']):
            self.nextObservation+=1
        # print(self.limit)
        self.reward = None
        self.possibleGain = 0
        self.openValue = 0
        self.closeValue = 0
        self.callback=callback


    def step(self, action):
        self.reward=0
        weekList = []
        dayList = []

        dayList=self.dayData.get(self.history[self.currentObservation]['Date'])
        weekList=self.weekData.get(self.history[self.currentObservation]['Date'])
        
        currentData = self.history[self.currentObservation-self.observationWindow:self.currentObservation] 

        currentData=currentData + dayList + weekList

        closeMinusOpen=list(map(lambda x: (x["Close"]-x["Open"])/x["Open"],currentData))
        # high=list(map(lambda x: x["High"],currentData))
        # low=list(map(lambda x: x["Low"],currentData))
        # volume=list(map(lambda x: x["Volume"],currentData))

        self.nextObservation=0
        while(self.history[self.currentObservation]['Date']==self.history[(self.currentObservation+self.nextObservation)%self.limit]['Date']):
            self.closeValue=self.history[(self.currentObservation+self.nextObservation)%self.limit]['Close']
            self.nextObservation+=1

        self.openValue = self.history[self.currentObservation]['Open']
        self.possibleGain = (self.closeValue - self.openValue)/self.openValue
        if(action == 1):
            self.reward = self.possibleGain-self.operationCost
        elif(action==2):
            self.reward = (-self.possibleGain)-self.operationCost
        else:
            self.reward = 0


        #self.currentObservation+=self.nextObservation

        self.done=True

        if(self.callback!=None and self.done):
            self.callback.on_episode_end(action,self.reward,self.possibleGain)
        


        
        state = numpy.array([closeMinusOpen])
        #state = numpy.array([closeMinusOpen,high,low,volume])
        #print(str(action) + " " + str(self.reward))

        #reward=self.reward*20 if(self.reward<0) else self.reward
        if(self.output):
            self.ensamble.at[self.history[self.currentObservation]['Date'],self.columnName]=action
        
        
        return state, self.reward, self.done, {}
        

    def reset(self):
        self.done = False
        self.episodio+=1
        self.nextObservation=0
        while(self.history[self.currentObservation]['Date']==self.history[(self.currentObservation+self.nextObservation)%self.limit]['Date']):
            self.nextObservation+=1
            if((self.currentObservation+self.nextObservation)>=self.limit):
                print("Balordo: episodio " + str(self.episodio) )
            
        #print(self.limit)
        self.reward = None
        self.possibleGain = 0
        self.openValue = 0
        self.closeValue = 0

        
        
        dayList = []
        weekList = []



        dayList=self.dayData.get(self.history[self.currentObservation]['Date'])
        weekList=self.weekData.get(self.history[self.currentObservation]['Date'])
        
        currentData = self.history[self.currentObservation-self.observationWindow:self.currentObservation] 

        currentData=currentData + dayList + weekList

        self.currentObservation+=self.nextObservation
        self.currentObservation%=self.limit

        if(self.currentObservation<self.observationWindow):
            self.currentObservation=self.observationWindow
            self.reset()
        self.nextObservation=0
        closeMinusOpen=list(map(lambda x: (x["Close"]-x["Open"])/x["Open"],currentData))
        #high=list(map(lambda x: x["High"],currentData))
        #low=list(map(lambda x: x["Low"],currentData))
        #volume=list(map(lambda x: x["Volume"],currentData))

        
        state = numpy.array([closeMinusOpen])
        #state = numpy.array([closeMinusOpen,high,low,volume])
        return state

    def resetEnv(self):
        self.currentObservation=self.observationWindow
        self.episodio=1