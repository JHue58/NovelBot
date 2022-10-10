import base64
import hashlib
import json
import math
import os
import random
import time
import traceback
from io import BytesIO
from threading import Thread

import requests

import NovelDB.NovelDB as ndb
import simuse

# 基础设定
saveImg = True  # 是否保存生成的图片到本地   True:是 / False:否
max_task = 10  # 同时处理的最大任务数量
cd = 60  # 冷却时间  秒

# 群聊中的指令
command = "/ai"
command_p = "p"
command_l = "l"
command_m = "m"
command_help = "help"
command_more = "more"
command_xp = "xp"

# 私聊管理员的指令 建议不动
command_add = "/ai add "
command_remove = "/ai remove "

# API设置
novelAI_Url = "https://api.novelai.net/ai/generate-image"
fanyi_Url = "https://fanyi.youdao.com/translate?&doctype=json&type=ZH_CN2EN&i={}"
novelAI_Token = ""

# 默认的负面词条
uc_tags = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"

# help消息
help = "\n".join([
    "novelAI Bot指令:", "/ai p/l/m [关键字] [(可选)基础图] 生成纵向/横向/方形图",
    "/ai xp 查询xp,@群友可查询群友xp", "不同的关键字间用逗号隔开", "专有名词使用-或_连接",
    "{}可增加关键字权重,[]可减少关键字权重", "例如", "生成一张制服少女方形图", "/ai m seifuku,girl",
    "支持中文关键字(通过有道翻译成英文,因此建议使用英文)", "/ai more 可查看进阶指令", "更多的英文关键字见",
    "https://wiki.installgentoo.com/wiki/Stable_Diffusion#Keywords\nhttps://gelbooru.com/index.php?page=tags&s=list",
    "Tips:使用形容词描述效果可能会优于专有名词"
])

# more消息
more = "\n".join([
    "noveAI Bot进阶指令:",
    "/ai p [超参] [关键字] 根据超参生成纵向图",
    "/ai l [超参] [关键字] 根据超参生成横向图",
    '超参使用"key=value"格式指定',
    "例如",
    "①生成一张制服少女纵向图(指定seed为123456)",
    "/ai p seed=123456 seifuku girl",
    "②生成一张制服少女图(指定高度和宽度为都为512,seed为123456,此时横纵向图的设置会失效)",
    "/ai p height=512 width=512 seed=123456 seifuku girl",
    "常用超参:",
    "t/translate 是否开启翻译(默认开启,f/false为关闭)",
    "height 图片高度(与宽度必须成常见比例)",
    "width 图片宽度(与高度必须成常见比例)",
    "seed 种子(随机int数,用来避免生成重复图片)",
    "uc 负面词条",
    "高级超参:",
    "noise 细节噪声(default 0.2)",
    "scale 对tag服从度(default 12)",
    "strength 与原图相似度(0-1 越小越像)",
])


""" 以下为代码块,请不要随意修改 """


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


class PermissionError(Exception):

    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'PermissionError: ' + ErrorInfo

    def __str__(self):
        return self.errorinfo


class ParametersError(Exception):

    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'ParametersError: ' + ErrorInfo

    def __str__(self):
        return self.errorinfo


class RequestError(Exception):

    def __init__(self, ErrorInfo):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'RequestError: ' + ErrorInfo

    def __str__(self):
        return self.errorinfo


class TaskMaxError(Exception):

    def __init__(self):
        super().__init__(self)  # 初始化父类
        self.errorinfo = 'TaskMaxError: ' + f'当前处理中的任务达到最大值{max_task}'

    def __str__(self):
        return self.errorinfo


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
        except RequestError as r:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                CT.Send_Message(self.groupId, 1,
                                "出现错误,请联系bot主人解决\n{}".format(r), 1)
                if self.sender != 0:
                    com.removeSender(self.sender)
                print(errorStr)
        except ParametersError as p:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                CT.Send_Message(self.groupId, 1,
                                "出现错误,请联系bot主人解决\n{}".format(p), 1)
                if self.sender != 0:
                    com.removeSender(self.sender)
                print(errorStr)
        except PermissionError as pe:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                CT.Send_Message(self.groupId, 1,
                                "出现错误,请联系bot主人解决\n{}".format(pe), 1)
                if self.sender != 0:
                    com.removeSender(self.sender)
                print(errorStr)
        except Exception as e:
            if self.groupId != 0:
                errorStr = traceback.format_exc()
                CT.Send_Message(self.groupId, 1,
                                "出现错误,请联系bot主人解决\n{}".format(errorStr), 1)
                if self.sender != 0:
                    com.removeSender(self.sender)
                print(errorStr)
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
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
    uc = uc_tags
    ucPreset = 0
    parm = {}

    parameters = {}

    model = "safe-diffusion"
    can_translate = True

    def __init__(self, switch: str):
        if switch == 'p':  # 纵向图
            self.height = 768
            self.width = 512
        elif switch == 'l':  # 横向图
            self.height = 512
            self.width = 768
        elif switch == 'm':  #方形图
            self.height = 512
            self.width = 512
        self.seed = getSeed()
        self.defaultData()

    def setImageParameter(self, img_url: str):
        res = requests.get(img_url)
        img_base64 = base64.b64encode(BytesIO(
            res.content).read()).decode('utf-8')
        self.parameters['image'] = img_base64

    def setParameter(self, key: str, value: str, sender: str):
        if key == 'model':
            if not (setting.hasAdmin(sender)):
                raise PermissionError("你没有权限修改该参数 {}".format(key))
            if not (value in ['safe', 'nai', 'furry']):
                raise ParametersError("错误的超参设置 {}".format(key))
            self.model = '{}-diffusion'.format(value)
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
        if key=='uc':
            value = value.replace('，',',')
            self.parameters[key] = self.parameters[key]+','+value
        else:
            self.parameters[key] = value

    def getParameter(self):
        #print(self.parameters)
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

    def __init__(self) -> None:
        if not (os.path.exists('config.json')):
            self.setting = {"admin": [], "group": []}
            self.save()
        else:
            self.setting = json.load(open("config.json", 'r',
                                          encoding='utf-8'))

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

    def save(self):
        json.dump(self.setting, open("config.json", 'w', encoding='utf-8'))

    def getCommand(self, text, sender):
        if text[:len(command_add)] == command_add:
            self.addGroup(text[len(command_add):], sender)
        elif text[:len(command_remove)] == command_remove:
            self.removeGroup(text[len(command_remove):], sender)
        else:
            return None


class commandSender():
    sender = {}
    dealing = []

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
            if command_list[1] == command_help:
                return 0
            elif command_list[1] == command_more:
                return -1
            elif command_list[1] == command_xp:
                return -2
            elif command_list[1] == command_p:
                return 1
            elif command_list[1] == command_l:
                return 2
            elif command_list[1] == command_m:
                return 3
            else:
                return 4
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
            "是否调用翻译:{}".format(translate_flag),
            "是否采用图片合成:{}".format(has_image),
            "seed:{}".format(parm.getParameter()['seed']),
            "请求关键字:{}".format(tags),
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
            parm.setParameter(key_value[0], key_value[1], sender)
            delvalue.append(command_list[i])
    for value in delvalue:
        command_list.remove(value)

    return ' '.join(command_list)


def translate(str):
    res = requests.get(fanyi_Url.format(str))
    res = json.loads(res.text)
    translateResult = res["translateResult"]
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
    if len(tags) < 3 or tags[2] == "":
        com.removeSender(qq)
        emptyReply(qq, groupID)
        return None

    tags: str = tags[2]
    tags = tags.replace('，', ',')
    tags_list: list = tags.split(',')

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
        "content-type":
        "application/json",
        "Content-Length":
        str(len(json.dumps(data).replace(' ', ''))),
        "Host":
        "api.novelai.net",
        "authorization":
        novelAI_Token
    }


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
    except:
        raise RequestError("请求错误 {}".format(result))
    base64 = res_dict['data']
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
          tags=tags)


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


def getReplyImage(messagechain: list):
    if len(messagechain) < 2:
        return messagechain

    quote_message = messagechain[1]
    if quote_message['type'] != 'Quote':
        return messagechain

    reply_message = quote_message['origin']
    # TODO 通过引用回复执行指令
    new_messagechain = []
    new_messagechain.append(messagechain[0])

    for index in range(len(reply_message)):
        img_message = reply_message[index]
        if img_message['type'] == 'Image':
            new_messagechain.append(img_message)
            break
    else:
        return messagechain

    for index in range(2, len(messagechain)):
        plain_message = messagechain[index]
        if plain_message['type'] == 'Plain':
            new_messagechain.insert(1, plain_message)
            break
    else:
        return messagechain

    print(new_messagechain)
    return new_messagechain


def reply(qq, groupID, msgID, base64: str, originChain: list, parm: Parameters,
          tags: str):

    del originChain[0]

    msg = [{
        'type': 'Quote',
        'senderId': qq,
        'targetId': groupID,
        'groupId': groupID,
        'id': msgID,
        'origin': originChain
    }]
    msg.append({'type': 'At', 'target': qq, 'display': ''})
    msg.append({'type': 'Image', 'base64': base64})
    msg.append({
        'type': 'Plain',
        'text': '关键字:{}\nseed:{}'.format(tags, parm.parameters['seed'])
    })
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

                    #messagechain = getReplyImage(messagechain)
                    try:
                        k = messagechain[1]
                    except:
                        continue
                    if k['type'] == 'Plain':
                        flag = com.getCommand(k['text'])
                        if flag == 0:
                            CT.Send_Message(group, 1, help, 1)
                        elif flag == -1:
                            CT.Send_Message(group, 1, more, 1)
                        elif flag == -2:
                            thread = MyThread(target=searchXP,
                                              args=(messagechain, group,
                                                    sender))
                            thread.start()
                        elif flag == 1:
                            if com.canTarget(sender, group):
                                com.doProcess(qq=sender,
                                              groupID=group,
                                              msg=messagechain,
                                              parm=Parameters('p'))

                            else:
                                continue
                        elif flag == 2:
                            if com.canTarget(sender, group):
                                com.doProcess(qq=sender,
                                              groupID=group,
                                              msg=messagechain,
                                              parm=Parameters('l'))

                            else:
                                continue
                        elif flag == 3:
                            if com.canTarget(sender, group):
                                com.doProcess(qq=sender,
                                              groupID=group,
                                              msg=messagechain,
                                              parm=Parameters('m'))

                            else:
                                continue
                        elif flag == 4:
                            raise CommandError()
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
            CT.Send_Message(group, 1, c.errorinfo, 1)
        except TaskMaxError as t:
            errorStr = traceback.format_exc()
            CT.Send_Message(group, 1, "出现错误,请联系bot主人解决\n{}".format(t), 1)
            com.removeSender(sender)
            print(errorStr)
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
    setting = config()
    CT = simuse.Client()
    com = commandSender()
    log = Logger()
    start()
