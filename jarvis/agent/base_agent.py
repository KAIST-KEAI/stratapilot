import os
import sys
import glob
from jarvis.action.base_action import BaseAction
import importlib
from typing import Optional

class BaseAgent:
    """
    BaseAgent is the base class of all agents.
    """
    def __init__(self, config_path=None):
        self.llm = None
        self.environment = None
        self.action_lib = {}
        self.action_lib_description = {}
        self.action = None
        self.init_action_lib()
    #
    # def from_config(self, config_path=None):
    #     raise NotImplementedError

    def init_action_lib(self, path=None, attribute_name='_description'):
        if not path:
            path = os.path.abspath(os.path.join(__file__, "..", "..", "action_lib"))
        sys.path.append(path)
        files = glob.glob(path + "/*.py")
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> e37198f (add travel eval)
        for file in files:
            if file.endswith('.py') and "__init__" not in file:
                class_name = file[:-3].split('/')[-1]  # 去除.py后缀，获取类名
                module = importlib.import_module(class_name)
<<<<<<< HEAD
                tmp_obj = getattr(module, class_name)()
                self.action_lib.update({class_name: tmp_obj})
                self.action_lib_description.update({class_name: tmp_obj.description})
=======
        # for file in files:
        #     if file.endswith('.py') and "__init__" not in file:
        #         class_name = file[:-3].split('/')[-1]  # 去除.py后缀，获取类名
        #         module = importlib.import_module(class_name)
        #         tmp_obj = getattr(module, class_name)()
        #         self.action_lib.update({class_name: tmp_obj})
        #         self.action_lib_description.update({class_name: tmp_obj.description})
>>>>>>> e3c3923 (dev SkillCreator)

=======
                source_code = inspect.getsource(module) # wzm修改，通过自省获得文件源码
                tmp_obj = getattr(module, class_name)() #存储对象方式
                # 存储源码字符串
                self.action_lib.update({class_name:  source_code})# wzm修改，技能库存储文件源码而不是对象
                # self.action_lib.update({class_name: tmp_obj})
                self.action_lib_description.update({class_name: tmp_obj.description})
>>>>>>> e37198f (add travel eval)

if __name__ == '__main__':
    a = BaseAgent()
    a.init_action_lib()
    for k,v in a.action_lib.items():
        print(k)
        print(v())