import base64
import hashlib
import json
import math
import os
import random
from re import L
import time
import traceback
import ahocorasick
from io import BytesIO
from threading import Thread

import requests

import NovelDB.NovelDB as ndb
import simuse

# 基础设定
saveImg = True  # 是否保存生成的图片到本地   True:是 / False:否
max_task = 10  # 同时处理的最大任务数量
cd = 60  # 冷却时间  秒
zero_cd_member = [1812303545] # 不计算cd的qq号,管理员默认无cd
a_day_limit = 20 # 每人每日的最大使用次数
filter_tag = True # 是否进行tag过滤
img_buffer_max = 10 # 最大图片缓存数


# 群聊中的指令
command = "/ai"
command_p = "p"
command_l = "l"
command_m = "m"
command_help = "help"
command_more = "more"
command_xp = "xp"
command_sampler = "sampler"

# 各指令对应的图像的宽和高
command_to_size = {
    "p":[512,768],
    "l":[768,512],
    "m":[640,640],
    "sp":[384,640],
    "sl":[640,384],
    "sm":[512,512],
    "lp":[512,1024],
    "ll":[1024,512],
    "lm":[1024,1024],
}

# 次数消耗(按宽/高分别计算)
a_day_limit_ma = {
    640:0,
    768:1,
    1024:2
}
# img2img2消耗(当消耗次数为0时才计算)
img2img_ma = 1

# 私聊管理员的指令 建议不动
command_add = "/ai add "  # 添加开启的群
command_remove = "/ai remove "  # 移除开启的群
command_delete_count = "/ai delete " # 清除某人的当日使用次数
command_use = "/ai use" # 查询使用情况

# API设置
novelAI_Url = "https://api.novelai.net/ai/generate-image"
fanyi_Url = "https://fanyi.youdao.com/translate?&doctype=json&type=ZH_CN2EN&i={}"
novelAI_Token = ""

# 负面词条枚举 可自定义新枚举值,normal必须要有
uc_tags = {
    "nonuse":
    "",
    "normal":
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
    "more":
    "nipple,ugly,duplicate,morbid,mutilated,tranny,trans,trannsexual,hermaphrodite,out of frame,extra fingers,mutated hands,poorly drawn hands,poorly drawn face,mutation,deformed,blurry,bad anatomy,bad proportions,extra limbs,cloned face,disfigured,more than 2 nipples,out of frame,extra limbs,gross proportions,malformed limbs,missing arms,missing legs,extra arms,extra legs,mutated hands,fused fingers,too many fingers,long neck",
    "senior":
    "multiple_breasts,(mutated_hands_and_fingers:1.5),(long_body:1.3),(mutation,poorly_drawn:1.2),black-white,bad_anatomy,liquid_body,liquid_tongue,disfigured,malformed,mutated,anatomical_nonsense,text_font_ui,error,malformed_hands,long_neck,blurred,lowers,lowres,bad_anatomy,bad_proportions,bad_shadow,uncoordinated_body,unnatural_body,fused_breasts,bad_breasts,huge_breasts,poorly_drawn_breasts,extra_breasts,liquid_breasts,heavy_breasts,missing_breasts,huge_haunch,huge_thighs,huge_calf,bad_hands,fused_hand,missing_hand,disappearing_arms,disappearing_thigh,disappearing_calf,disappearing_legs,fused_ears,bad_ears,poorly_drawn_ears,extra_ears,liquid_ears,heavy_ears,missing_ears,fused_animal_ears,bad_animal_ears,poorly_drawn_animal_ears,extra_animal_ears,liquid_animal_ears,heavy_animal_ears,missing_animal_ears,text,ui,error,missing_fingers,missing_limb,fused_fingers,one_hand_with_more_than_5_fingers,one_hand_with_less_than_5_fingers,one_hand_with_more_than_5_digit,one_hand_with_less_than_5_digit,extra_digit,fewer_digits,fused_digit,missing_digit,bad_digit,liquid_digit,colorful_tongue,black_tongue,cropped,watermark,username,blurry,JPEG_artifacts,signature,3D,3D_game,3D_game_scene,3D_character,malformed_feet,extra_feet,bad_feet,poorly_drawn_feet,fused_feet,missing_feet,extra_shoes,bad_shoes,fused_shoes,more_than_two_shoes,poorly_drawn_shoes,bad_gloves,poorly_drawn_gloves,fused_gloves,bad_cum,poorly_drawn_cum,fused_cum,bad_hairs,poorly_drawn_hairs,fused_hairs,big_muscles,ugly,bad_face,fused_face,poorly_drawn_face,cloned_face,big_face,long_face,bad_eyes,fused_eyes_poorly_drawn_eyes,extra_eyes,malformed_limbs,more_than_2_nipples,missing_nipples,different_nipples,fused_nipples,bad_nipples,poorly_drawn_nipples,black_nipples,colorful_nipples,gross_proportions,short_arm,(((missing_arms))),missing_thighs,missing_calf,missing_legs,mutation,duplicate,morbid,mutilated,poorly_drawn_hands,more_than_1_left_hand,more_than_1_right_hand,deformed,(blurry),disfigured,missing_legs,extra_arms,extra_thighs,more_than_2_thighs,extra_calf,fused_calf,extra_legs,bad_knee,extra_knee,more_than_2_legs,bad_tails,bad_mouth,fused_mouth,poorly_drawn_mouth,bad_tongue,tongue_within_mouth,too_long_tongue,black_tongue,big_mouth,cracked_mouth,bad_mouth,dirty_face,dirty_teeth,dirty_pantie,fused_pantie,poorly_drawn_pantie,fused_cloth,poorly_drawn_cloth,bad_pantie,yellow_teeth,thick_lips,bad_cameltoe,colorful_cameltoe,bad_asshole,poorly_drawn_asshole,fused_asshole,missing_asshole,bad_anus,bad_pussy,bad_crotch,bad_crotch_seam,fused_anus,fused_pussy,fused_anus,fused_crotch,poorly_drawn_crotch,fused_seam,poorly_drawn_anus,poorly_drawn_pussy,poorly_drawn_crotch,poorly_drawn_crotch_seam,bad_thigh_gap,missing_thigh_gap,fused_thigh_gap,liquid_thigh_gap,poorly_drawn_thigh_gap,poorly_drawn_anus,bad_collarbone,fused_collarbone,missing_collarbone,liquid_collarbone,strong_girl,obesity,worst_quality,low_quality,normal_quality,liquid_tentacles,bad_tentacles,poorly_drawn_tentacles,split_tentacles,fused_tentacles,missing_clit,bad_clit,fused_clit,colorful_clit,black_clit,liquid_clit,QR_code,bar_code,censored,safety_panties,safety_knickers,beard,furry,pony,pubic_hair,mosaic,excrement,faeces,shit,futa,testis",
}

# 需要admin权限使用的高级参数
admin_parm = [
    'model',
    'steps',
]

# sampler枚举
sampler_list = [
    "k_euler_ancestral",
    "k_euler",
    "k_lms",
    "plms",
    "ddim"
] 

# help消息
help = "\n".join([
    "novelAI Bot指令:", "/ai [(可选)*大小][*形状] [关键字] [(可选)*高级参数] [(可选)*图片]",
    "*形状可选值:p/l/m(纵/横向/方形)",
    "*大小可选值:s/l(小,大 默认为中等 注意大小和形状两个参数间没有空格)",
    "*高级参数输入/ai more查看",
    "*图片也可通过回复的方式传入",
    "/ai xp 查询xp,@群友可查询群友xp", "不同的关键字间用逗号隔开", "专有名词使用-或_连接",
    "{}可增加关键字权重,[]可减少关键字权重", "例如", "生成一张制服少女方形图", "/ai m seifuku,girl",
    "支持中文关键字(通过有道翻译成英文,因此建议使用英文)", 
    "关键字生成器:http://aitag.top",
    "Tips:使用形容词描述效果可能会优于专有名词,有时novelAI服务器抽风,出现长时间不出图是正常现象",
])

# more消息
more = "\n".join([
    "noveAI Bot进阶指令:",
    '参数使用"key=value"格式指定',
    "例如",
    "①生成一张制服少女纵向图(指定seed为123456)",
    "/ai p seifuku girl seed=123456",
    "②生成一张制服少女图(指定seed为123456,scale为18)",
    "/ai p seifuku girl seed=123456 scale=18",
    "常用参数:",
    "t/translate 是否开启翻译(默认开启,f/false为关闭)",
    "height 图片高度(64的倍数)",
    "width 图片宽度(64的倍数)",
    "seed 种子(随机int数,用来避免生成重复图片)",
    "uclevel 负面词条等级(nonuse 不使用,normal 默认,more 多,senior 更多)",
    "高级参数:",
    "uc (增加负面词条 在指令的末尾输入)",
    "noise 细节噪声(default 0.2)",
    "scale 对tag服从度(default 12)",
    "strength 与原图相似度(0-1 越小越像)",
    "sampler 更换采样器,具体可输入/ai sampler查看",
    "Tips:等号两边不要有空格哦！请使用英文等号"
])

# sampler 消息
sampler = '可用的采样器:k_euler_ancestral(默认),k_euler,k_lms,plms,ddim'


""" 以下为代码块,请不要随意修改 """

# 版本控制
version = 6

# 更新广播
update_msg = "\n".join([
    "优化help的描述",
    "为方便手机用户，支持回复已发送的图片进行imgToimg",
    "版本未经测试，若出现bug请联系管理员"
])

def getSeed():
    times = time.time()
    random_times = random.uniform(times / 2, times)
    return int(times - random_times)


class CommandError(Exception):

    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = f'指令出错\n请输入/ai help查看帮助'

    def __str__(self):
        return self.errorinfo

class TranslateError(Exception):
    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'TranslateError: 翻译失败(无法请求有道翻译服务),请使用英文tag或者不使用翻译'

    def __str__(self):
        return self.errorinfo

class ImageNotInBufferError(Exception):
    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'ImageNotInBufferError: 该图片已从缓存区中清除,请重新发送图片'

    def __str__(self):
        return self.errorinfo

class ForbiddenKeyWordError(Exception):
    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'ForbiddenKeyWordError: tag中包含有违禁词汇'

    def __str__(self):
        return self.errorinfo


class PermissionError(Exception):

    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'PermissionError: ' + ErrorInfo

    def __str__(self):
        return self.errorinfo

class UseMaxError(Exception):
    def __init__(self,need_count,count):
        super().__init__(self)  # 初始化父类
        self.errorinfo = f"UseMaxError: 本次请求需要消耗{need_count}次使用次数,您当日剩余次数为{a_day_limit-count}次，明天再来吧！"

    def __str__(self):
        return self.errorinfo


class ParametersError(Exception):

    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'ParametersError: ' + ErrorInfo

    def __str__(self):
        return self.errorinfo

class KeyWordError(Exception):
    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'KeyWordError: 关键字不能为空'

    def __str__(self):
        return self.errorinfo

class RequestError(Exception):

    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        if len(ErrorInfo)>500:
            ErrorInfo = '字符串过长,无法显示'
        self.errorinfo = 'RequestError: ' + ErrorInfo

    def __str__(self):
        return self.errorinfo


class TaskMaxError(Exception):

    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'TaskMaxError: ' + f'当前处理中的任务达到最大值{max_task}'

    def __str__(self):
        return self.errorinfo

class ImageBuffer():
    group_sourceID_dict = {} # {'group':{'sourceID':'url'}}

    def getImageUrl(self,groupID,sourceID):
        try:
            sourceid_dict = self.group_sourceID_dict[groupID]
            url = sourceid_dict[sourceID]
        except KeyError:
            raise ImageNotInBufferError()

        return url

    def appendImage(self,groupID,sourceID,url):
        if not(groupID in self.group_sourceID_dict.keys()):
            self.group_sourceID_dict[groupID] = {}
        sourceid_dict:dict = self.group_sourceID_dict[groupID]
        if len(sourceid_dict) > img_buffer_max:
            sourceid_dict.pop(min(sourceid_dict))
        sourceid_dict[sourceID] = url

    def scanfImage(self,groupID,msg):
        if len(msg)<=0:
            return
        source_msg = msg[0]
        sourceID = source_msg['id']
        
        url = ''
        for img_msg in msg:
            if img_msg['type']=='Image':
                url = img_msg['url']
        if url=='':
            return None
        self.appendImage(groupID,sourceID,url)

    def sancfImageFromQuote(self,group,msg):
        if len(msg) <=2:
            return msg
        quote_msg = msg[1]
        if quote_msg['type']!='Quote':
            return msg
    
        plain_msg = {}
        for i in msg:
            if i['type']!='Plain':
                continue
            else:
                plain_msg = i
        if plain_msg=={}:
            return msg
        text:str = plain_msg['text'].strip()
        if text[:len(command)]!=command:
            return msg
        plain_msg['text'] = text
        sourceID = quote_msg['id']
        new_msg = [msg[0],plain_msg,{'type':'Image','url':self.getImageUrl(group,sourceID)}]
        return new_msg
        



class MyThread(Thread):
    groupId = 0
    sender = 0

    def setGroupId(self, groupID):
        self.groupId = groupID

    def setSender(self, sender):
        self.sender = sender

    def run(self):
        """Method representing the thread's activity.

        You may override this method in a subclass. The standard run() method
        invokes the callable object passed to the object's constructor as the
        target argument, if any, with sequential and keyword arguments taken
        from the args and kwargs arguments, respectively.

        """
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
        except UseMaxError as u:
            if self.groupId!=0:
                msg = [
                    {'type':'At','target':self.sender,'display':''},
                    {'type':'Plain','text':f'\n{u}'}
                ]
                CT.Send_Message_Chain(self.groupId,1,msg)
        except RequestError as r:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                msg = [
                    {'type':'At','target':self.sender,'display':''},
                    {'type':'Plain','text':f'出现错误,请联系bot主人解决\n{r}'}
                ]
                CT.Send_Message_Chain(self.groupId,1,msg)
                print(errorStr)
        except ParametersError as p:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                msg = [
                    {'type':'At','target':self.sender,'display':''},
                    {'type':'Plain','text':f'出现错误,请联系bot主人解决\n{p}'}
                ]
                CT.Send_Message_Chain(self.groupId, 1,msg)
                print(errorStr)
        except PermissionError as pe:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                msg = [
                    {'type':'At','target':self.sender,'display':''},
                    {'type':'Plain','text':f'出现错误,请联系bot主人解决\n{pe}'}
                ]
                CT.Send_Message_Chain(self.groupId, 1,msg)
                print(errorStr)
        except KeyWordError as kw:
            if self.groupId != 0:
                emptyReply(qq=self.sender,groupID=self.groupId)
        except TranslateError as tr:
            if self.groupId != 0:
                msg = [
                    {'type':'At','target':self.sender,'display':''},
                    {'type':'Plain','text':f'\n{tr}'}
                ]
                CT.Send_Message_Chain(self.groupId,1,msg)
        except Exception as e:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                msg = [
                    {'type':'At','target':self.sender,'display':''},
                    {'type':'Plain','text':f'\n{errorStr}'}
                ]
                CT.Send_Message_Chain(self.groupId, 1,msg)
                print(errorStr)
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            if self.sender != 0:
                    com.removeSender(self.sender)
            del self._target, self._args, self._kwargs


class Parameters():
    height = 0
    width = 0
    n_samples = 1
    noise = 0.2
    sampler = "k_euler_ancestral"
    scale = 12
    seed = 0
    steps = 28
    strength = 0.7
    uc = uc_tags['normal']
    ucPreset = 0
    parm = {}

    parameters = {}

    model = "safe-diffusion"
    uc_level = "normal"
    new_uc = ""
    can_translate = True
    img2img = False

    def __init__(self, switch: str):
        sizes = command_to_size[switch]
        self.width = sizes[0]
        self.height = sizes[1]
        self.seed = getSeed()
        self.defaultData()

    def setImageParameter(self, img_url: str):
        res = requests.get(img_url)
        img_base64 = base64.b64encode(BytesIO(
            res.content).read()).decode('utf-8')
        self.parameters['image'] = img_base64
        self.img2img = True

    def setParameter(self, key: str, value: str, sender: str):
        if key in admin_parm and not (setting.hasAdmin(sender)):
            raise PermissionError("你没有权限修改该参数 {}".format(key))

        if key == 'model':
            if not (value in ['safe', 'nai', 'furry']):
                raise ParametersError("错误的超参设置 {}".format(key))
            self.model = '{}-diffusion'.format(value)
            return
        if key == 'uclevel':
            if not (value in uc_tags.keys()):
                raise ParametersError("不存在的负面词条等级枚举 {}".format(key))
            self.uc = uc_tags[value]
            self.uc_level = value
            return
        if key == 'sampler':
            if not (value in sampler_list):
                raise ParametersError("不存在的采样器枚举,请输入/ai sampler查看 {}".format(key))
            self.sampler = value
            self.parameters[key] = value
            return
        if key == 't' or key == 'translate':
            if not (value in ['t', 'f', 'true', 'false']):
                raise ParametersError("错误设置 {}".format(key))
            if value == 't' or value == 'true':
                self.can_translate = True
            else:
                self.can_translate = False
            return

        if not (key in self.parameters.keys()):
            raise ParametersError("错误的超参设置 {}".format(key))
        if key == "parm":
            return
        if not (key in ["sampler", "uc"]):
            value = float(value)
        if key in ["scale", "n_samples", "steps", "seed", "height", "width"]:
            value = int(value)
        if key == 'uc':
            value = value.replace('，', ',')
            self.new_uc = value
        else:
            self.parameters[key] = value

    def getParameter(self):
        #print(self.parameters)
        if self.new_uc != "":
            self.parameters['uc'] = self.parameters['uc'] + "," + self.new_uc
        return self.parameters

    def defaultData(self):
        data = {
            "height": self.height,
            "n_samples": self.n_samples,
            "noise": self.noise,
            "sampler": self.sampler,
            "scale": self.scale,
            "seed": self.seed,
            "steps": self.steps,
            "strength": self.strength,
            "uc": self.uc,
            "ucPreset": self.ucPreset,
            "width": self.width,
            "parm": self.parm
        }
        self.parameters = data
        return data


class config():
    setting = {}
    filter_tag = []


    def __init__(self) -> None:
        if not (os.path.exists('config.json')):
            self.setting = {"admin": [], "group": [],"version":version}
            self.save()
        else:
            self.setting = json.load(open("config.json", 'r',
                                          encoding='utf-8'))
        zero_cd_member.extend(self.setting['admin'])
        self.updateBroadcast()
        self.initFilter()

    def updateBroadcast(self):
        if self.needBroadcast():
            for group in self.setting['group']:
                CT.Send_Message(group,1,'版本更新完毕:\n'+update_msg,1)
            self.setting['version'] = version
            self.save()

    def initFilter(self):
        
        if filter_tag==True:
            with open('filter.txt','r',encoding='utf-8-sig') as f:
                for line in f:
                    rs = line.rstrip('\n')
                    self.filter_tag.append(rs)

    def build_actree(self,wordlist):
        actree = ahocorasick.Automaton()
        for index, word in enumerate(wordlist):
            actree.add_word(word, (index, word))
        actree.make_automaton()
        return actree

    def FilterTag(self,sender,tags:str):

        if filter_tag == False:
            return tags
        if self.hasAdmin(sender):
            return tags
        actree = self.build_actree(wordlist=self.filter_tag)
        sent_cp = tags
        for i in actree.iter(tags):
            sent_cp = sent_cp.replace(i[1][1], "")
        return sent_cp
    
    def needBroadcast(self):
        if not('version' in self.setting.keys()):
            return True
        if self.setting['version']<version:
            return True
        return False
            

    def hasGroup(self, groupId):
        groups: list = self.setting['group']
        return groupId in groups

    def hasAdmin(self, sender):
        admins: list = self.setting['admin']
        return sender in admins

    def addGroup(self, groupId, sender):
        groupId = int(groupId)
        groups: list = self.setting['group']
        if not (groupId in groups):
            groups.append(groupId)
            CT.Send_Message(sender, 2, "添加成功", 1)
            self.save()
        else:
            CT.Send_Message(sender, 2, "添加失败,已存在", 1)
        self.setting['group'] = groups

    def removeGroup(self, groupId, sender):
        groupId = int(groupId)
        groups: list = self.setting['group']
        if groupId in groups:
            groups.remove(groupId)
            CT.Send_Message(sender, 2, "删除成功", 1)
            self.save()
        else:
            CT.Send_Message(sender, 2, "删除失败,不存在", 1)
        self.setting['group'] = groups

    def getDayUse(self,sender):
        sender = int(sender)
        use_list = ndb.getAllUseCount()
        msg = "当日使用情况如下:"
        for use in use_list:
            msg = msg + f"\n{use[0]} : {use[1]}次"

        CT.Send_Message(sender,2,msg,1)

    def deleteUse(self,target,sender):
        target = int(target)
        ndb.deleteUseCount(target)
        CT.Send_Message(sender, 2, "已更新", 1)

    def save(self):
        json.dump(self.setting, open("config.json", 'w', encoding='utf-8'))

    def getCommand(self, text, sender):
        if text[:len(command_add)] == command_add:
            self.addGroup(text[len(command_add):], sender)
        elif text[:len(command_remove)] == command_remove:
            self.removeGroup(text[len(command_remove):], sender)
        elif text[:len(command_delete_count)] == command_delete_count: 
            self.deleteUse(text[len(command_remove):], sender)
        elif text[:len(command_use)] == command_use:
            self.getDayUse(sender)
        else:
            return None


class commandSender():
    sender = {}
    dealing = []
    sender_use_count = {}

    # TODO 从数据库记录/读取
    def loadUseCountFromDB(self):
        pass

    def useCount(self,sender,width,height):
        pass

    def getTaskNum(this) -> int:
        return len(this.dealing)

    def taskIsFull(this) -> bool:
        if this.getTaskNum() >= max_task:
            return True
        else:
            return False

    def removeSender(this, sender: str):
        if sender in this.dealing:
            this.dealing.remove(sender)

    def getCommand(this, text: str):
        try:
            command_list = text.split()
            if command_list == None or len(command_list) < 1:
                return None
            if command_list[0] != command:
                return None
            if command_list[1] in command_to_size.keys():
                return command_list[1]
            if command_list[1] == command_help:
                return 0
            if command_list[1] == command_more:
                return 1
            if command_list[1] == command_xp:
                return 2
            if command_list[1] == command_sampler:
                return 3
    
            
            return -1
        except IndexError:
            raise CommandError()

    def canTarget(this, qq, groupID):
        if not (qq in this.sender.keys()) and not (qq in this.dealing):
            return True
        if qq in this.dealing:
            waittingReply(qq, groupID)
            return False
        times = this.sender[qq]
        cdtime = time.time() - times
        if cdtime > cd:
            return True
        else:
            errorReply(qq=qq, groupID=groupID, cdtime=cd - cdtime)
            return False

    def doProcess(this, qq, groupID, msg, parm):
        if com.taskIsFull():
            raise TaskMaxError()

        this.dealing.append(qq)
        thread = MyThread(target=novelAI, args=(msg, qq, groupID, parm))
        thread.setGroupId(groupID)
        thread.setSender(qq)
        thread.start()
        print(f'[{time.time()}] 获取到任务 正在处理中的任务数量:{com.getTaskNum()}')

    def success(this, qq):
        this.removeSender(qq)
        if not(qq in zero_cd_member):
            this.sender[qq] = time.time()


class Logger():
    start_time = time.strftime("%Y-%m-%d %Hh %Mm %Ss")
    log_path = 'logs/' + start_time
    img_path = log_path + '/img'
    img_to_img_path = img_path + '/img2img'

    def __init__(self) -> None:
        if not (os.path.exists(self.log_path)):
            os.makedirs(self.log_path)
            os.makedirs(self.img_path)
            os.makedirs(self.img_to_img_path)

    def async_start(self, func, args: tuple, groupID=None):
        thread = MyThread(target=func, args=args)
        if groupID != None:
            thread.setGroupId(groupID)

        thread.start()

    def saveImg(self, img_base64: str, parm: Parameters, img_hash: str):

        if 'image' in parm.parameters.keys():
            self.saveImg2Img(img_base64, img_hash, parm)
        else:
            base64_hex = base64.b64decode(img_base64)
            path = "{}/{}.jpg".format(self.img_path, img_hash)
            if not (os.path.exists(path)):
                with open(path, 'wb') as img_file:
                    img_file.write(base64_hex)

    def saveImg2Img(self, img_base64_new: str, new_hash, parm: Parameters):
        img_base64_orgin: str = parm.parameters['image']
        hash = hashlib.md5()
        hash.update(img_base64_orgin.encode('utf-8'))
        hash = hash.hexdigest()
        path = "{}/{}.jpg".format(self.img_to_img_path, hash)
        if not (os.path.exists(path)):
            base64_hex = base64.b64decode(img_base64_orgin)
            with open(path, 'wb') as img_file:
                img_file.write(base64_hex)

        new_path = "{}/{}_new_{}.jpg".format(self.img_to_img_path, hash,
                                             new_hash)
        if not (os.path.exists(new_path)):
            base64_hex = base64.b64decode(img_base64_new)
            with open(new_path, 'wb') as img_file:
                img_file.write(base64_hex)

    def printLogger(self, tags, command_list, groupID, qq, translate_flag,
                    parm: Parameters, img_hash: str):

        ndb.insertTagsToDB(qq, tags)

        has_image = False
        if 'image' in parm.parameters.keys():
            has_image = True
        logger = '\n'.join([
            "请求时间:{}".format(time.strftime("%Y-%m-%d %H:%M:%S")),
            "请求QQ号:{}".format(qq),
            "请求群号:{}".format(groupID),
            "模式:{}".format(command_list[1]),
            "model:{}".format(parm.model),
            "sampler:{}".format(parm.sampler),
            "是否调用翻译:{}".format(translate_flag),
            "是否采用图片合成:{}".format(has_image),
            "负面词条等级:{}".format(parm.uc_level),
            "seed:{}".format(parm.getParameter()['seed']),
            "请求关键字:{}".format(tags),
            "负面词条:{}".format(parm.new_uc),
            "生成图Hash:{}".format(img_hash),
            "\n",
        ])
        print(logger)
        file = open(self.log_path + '/' + self.start_time + '.log',
                    'a',
                    encoding='utf-8')
        file.write(logger)
        file.close()


def setParameters(command_list: list, parm: Parameters, sender) -> str:

    delvalue = []
    for i in range(len(command_list)):
        if command_list[i].find('=') != -1:
            key_value = command_list[i].split('=')
            # 对uc超参的特殊处理
            if key_value[0] == 'uc':
                key_value[1] = key_value[1] +' '+' '.join(command_list[i+1:])
                parm.setParameter(key_value[0], key_value[1], sender)
                delvalue.extend(command_list[i:])
                break
            parm.setParameter(key_value[0], key_value[1], sender)
            delvalue.append(command_list[i])
    for value in delvalue:
        command_list.remove(value)

    return ' '.join(command_list)


def translate(str):
    try:
        res = requests.get(fanyi_Url.format(str))
        res = json.loads(res.text)
        translateResult = res["translateResult"]
    except:
        raise TranslateError()
    return translateResult[0][0]['tgt']


def is_contain_chinese(check_str):
    """
    判断字符串中是否包含中文
    :param check_str: {str} 需要检测的字符串
    :return: {bool} 包含返回True， 不包含返回False
    """
    for ch in check_str:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False

def isDayLimit(qq,need_count) ->int:
    count = ndb.getUseCount(qq)
    if count+need_count > a_day_limit:
        raise UseMaxError(need_count=need_count,count=count)
    else:
        return count

def getNeedCount(parm:Parameters):
    width = parm.parameters['width']
    height = parm.parameters['height']
    width_will_add = 0
    height_will_add = 0

    key_list = list(a_day_limit_ma.keys())
    key_list_len = len(key_list)
    for index in range(key_list_len):
        add = a_day_limit_ma[key_list[index]]
        if index==key_list_len-1:
            if width>=key_list[index]:
                width_will_add = add
            if height>=key_list[index]:
                height_will_add = add
            break
        if index==0:
            if width<=key_list[index]:
                width_will_add = add
            if height<=key_list[index]:
                height_will_add = add
            continue
        if key_list[index-1]<width<=key_list[index]:
            width_will_add = add
        if key_list[index-1]<height<=key_list[index]:
            height_will_add = add

    if parm.img2img and height_will_add==0 and width_will_add==0:
        return height_will_add+width_will_add+img2img_ma

    return height_will_add+width_will_add
        



def novelAI(msg, qq, groupID, parm: Parameters):

    for i in msg:
        if i['type'] == 'Image':
            parm.setImageParameter(i['url'])
            break

    source = msg[0]
    plain = msg[1]
    msgID = source['id']
    tags: str = plain['text']
    tags = setParameters(tags.split(), parm, qq)
    tags = ' '.join(tags.split())
    tags = tags.split(' ', 2)
    command_list = tags

    if not(setting.hasAdmin(qq)):
        need_count = getNeedCount(parm)
    else:
        need_count = 0
    count = isDayLimit(qq,need_count)


    

    tags: str = tags[2]
    tags = tags.replace('，', ',')
    tags = setting.FilterTag(qq,tags)
    if len(tags) < 3 or tags[2] == "":
        raise KeyWordError()
    tags_list = list(filter(None,tags.split(',')))

    translate_flag = False



    if parm.can_translate:
        for i in range(len(tags_list)):
            if is_contain_chinese(tags_list[i]):
                tags_list[i] = translate(tags_list[i])
                translate_flag = True

    tags = ','.join(tags_list)


    data = {
        "input": tags,
        "model": parm.model,
        "parameters": parm.getParameter()
    }

    Header = {
        "content-type": "application/json",
        "Content-Length": str(len(json.dumps(data).replace(' ', ''))),
        "Host": "api.novelai.net",
        "authorization": novelAI_Token
    }
    result = "获取API回调失败"
    try:
        res = requests.post(url=novelAI_Url,
                            headers=Header,
                            data=json.dumps(data).replace(' ', ''))
        result = res.text
        res = res.text
        res = res.split("\n")
        res = res[:3]
        res_dict = {}
        for i in res:
            temp = dict([tuple(i.split(':'))])
            res_dict.update(temp)
        base64 = res_dict['data']
    except:
        raise RequestError("请求错误 {}".format(result))
    hash = hashlib.md5()
    hash.update(base64.encode('utf-8'))
    hash = hash.hexdigest()

    log.async_start(func=log.printLogger,
                    args=(tags, command_list, groupID, qq, translate_flag,
                          parm, hash),
                    groupID=groupID)

    if saveImg:
        log.async_start(func=log.saveImg,
                        args=(base64, parm, hash),
                        groupID=groupID)

    reply(qq=qq,
          groupID=groupID,
          msgID=msgID,
          base64=base64,
          originChain=msg,
          parm=parm,
          tags=tags,
          need_count=need_count,
          count=count
          )

    ndb.addUseCount(qq,need_count)


def waittingReply(qq, groupID):
    msg = [{
        'type': 'At',
        'target': qq,
        'display': ''
    }, {
        'type': 'Plain',
        'text': '\n你还有任务正在进行中哦'
    }]
    CT.Send_Message_Chain(target_type=1, targets=groupID, messagechain=msg)


def emptyReply(qq, groupID):
    msg = [{
        'type': 'At',
        'target': qq,
        'display': ''
    }, {
        'type': 'Plain',
        'text': '\n关键字不能为空'
    }]
    CT.Send_Message_Chain(target_type=1, targets=groupID, messagechain=msg)


def errorReply(qq, groupID, cdtime):
    msg = [{
        'type': 'At',
        'target': qq,
        'display': ''
    }, {
        'type': 'Plain',
        'text': "\n你的冷却时间还有" + str(math.ceil(cdtime)) + "秒哦,待会再来吧"
    }]
    CT.Send_Message_Chain(target_type=1, targets=groupID, messagechain=msg)





def reply(qq, groupID, msgID, base64: str, originChain: list, parm: Parameters,
          tags: str,count:int,need_count:int):

    del originChain[0]

    tip_str = '关键字:{}\nseed:{}'.format(tags, parm.parameters['seed'])

    if parm.new_uc != "":
        tip_str = tip_str + "\n负面词条:{}".format(parm.new_uc)

    msg = [{
        'type': 'Quote',
        'senderId': qq,
        'targetId': groupID,
        'groupId': groupID,
        'id': msgID,
        'origin': originChain
    }]
    msg.append({'type': 'At', 'target': qq, 'display': ''})
    if need_count>0:
        msg.append({'type':'Plain','text':f'\n本次消耗次数{need_count}次,剩余次数{a_day_limit-count-need_count}次\n'})
    msg.append({'type': 'Image', 'base64': base64})
    msg.append({'type': 'Plain', 'text': tip_str})
    if 'image' in parm.parameters.keys():
        msg.append({'type': 'Plain', 'text': '\n图源:'})
        msg.append({'type': 'Image', 'base64': parm.parameters['image']})

    CT.Send_Message_Chain(groupID, 1, msg)
    com.success(qq)


def searchXP(msg: list, groupID, sender):
    if len(msg) != 2:
        At_msg = msg[2]
        if At_msg['type'] != 'At':
            return
        target = At_msg['target']
    else:
        target = sender

    tags_dict = ndb.getTagsCount(target)

    if tags_dict == None:
        CT.Send_Message(groupID, 1, "无法查询该群友的XP", 1)
        return

    xp_msg = ["\n你的XP如下:"]

    tag_list = list(tags_dict.keys())

    for index in range(len(tag_list)):
        line = "{}. {} : {}次".format(index + 1, tag_list[index],
                                     tags_dict[tag_list[index]])
        xp_msg.append(line)

    xp_msg = '\n'.join(xp_msg)

    xp_chain = [{
        'type': 'At',
        'target': target,
        'display': ''
    }, {
        'type': 'Plain',
        'text': xp_msg
    }]

    CT.Send_Message_Chain(groupID, 1, xp_chain)


def start():
    while True:
        try:
            message = CT.Fetch_Message()
            if type(message) == type(0):
                time.sleep(0.5)
                continue
            for i in message:
                
                if i['type'] == 'GroupMessage':
                    group = i['group']
                    sender = i['sender']
                    messagechain = i['messagechain']
                    
                    if not (setting.hasGroup(group)):
                        continue

                    messagechain = imgbuffer.sancfImageFromQuote(group,messagechain)
                    try:
                        k = messagechain[1]
                    except:
                        continue
                    imgbuffer.scanfImage(group,messagechain)
                    
                    if k['type'] == 'Plain':
                        flag = com.getCommand(k['text'])
                        if flag == 0:
                            CT.Send_Message(group, 1, help, 1)
                        elif flag == 1:
                            CT.Send_Message(group, 1, more, 1)
                        elif flag == 2:
                            thread = MyThread(target=searchXP,
                                              args=(messagechain, group,
                                                    sender))
                            thread.start()
                        elif flag == 3:
                            CT.Send_Message(group,1,sampler,1)
                        elif flag == -1:
                            raise CommandError()
                        elif flag == None:
                            continue
                        else:
                            if com.canTarget(sender, group):
                                com.doProcess(qq=sender,
                                              groupID=group,
                                              msg=messagechain,
                                              parm=Parameters(flag))

                            else:
                                continue

                elif i['type'] == 'FriendMessage':
                    sender = i['sender']
                    messagechain = i['messagechain']
                    if setting.hasAdmin(sender):
                        for k in messagechain:
                            if k['type'] == 'Plain':
                                setting.getCommand(k['text'], sender)
                                break
                    else:
                        continue
        except CommandError as c:
            
            msg = [
                {'type':'At','target':sender,'display':''},
                {'type':'Plain','text':'\n'+c.errorinfo}
                ]
            CT.Send_Message_Chain(group, 1, msg)
        except TaskMaxError as t:
            errorStr = traceback.format_exc()
            CT.Send_Message(group, 1, "出现错误,请联系bot主人解决\n{}".format(t), 1)
            com.removeSender(sender)
            print(errorStr)
            continue
        except ImageNotInBufferError as im:
            msg = [
                {'type':'At','target':sender,'display':''},
                {'type':'Plain','text':'\n'+im.errorinfo}
                ]
            CT.Send_Message_Chain(group, 1, msg)
            com.removeSender(sender)
            continue
        except Exception as e:
            errorStr = traceback.format_exc()
            CT.Send_Message(group, 1, "出现错误,请联系bot主人解决\n{}".format(errorStr),
                            1)
            com.removeSender(sender)
            print(errorStr)
            continue
        finally:
            time.sleep(0.5)


if __name__ == '__main__':
    CT = simuse.Client()
    setting = config()
    com = commandSender()
    log = Logger()
    imgbuffer = ImageBuffer()
    start()
