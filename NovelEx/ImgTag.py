import requests
import re


class ImageGetTagError(Exception):
    def __init__(self,err):
        super().__init__(self)  # 初始化父类
        self.errorinfo = f"ImageGetTagError: {err}"

    def __str__(self):
        return self.errorinfo


def getImgTag(img_io):

    url = "http://dev.kanotype.net:8003/deepdanbooru/upload"
    files = {
    "network_type":(None,"general"),
    "file":("0.png",img_io,"image/png")}
    try:
        response = requests.post(url, timeout = 60,files = files)
        data: str = response.text
    except:
        raise ImageGetTagError('请求超时')

    tags = re.findall(r'target="_blank">(.*)</a></td>',data)
    num = re.findall(r'<td>(\d+\.?\d+)</td>',data)
    data_dict = dict(zip(tags, num))
    a1 = sorted(data_dict.items(), key=lambda x: x[1],reverse=True)
    taglist = []
    for (a,b) in a1:
        taglist.append(a)
    tags :str = ",".join(taglist)
    tags = tags.replace("rating:safe,","")

    return tags
