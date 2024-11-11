import os
import sys
import glob
from jarvis.action.base_action import BaseAction
import importlib
from typing import Optional
<<<<<<< HEAD
=======
import inspect
import re
import json

>>>>>>> ac58871 (new example)

class BaseAgent:
    """
    BaseAgent is the base class of all agents.
    """
    def __init__(self, config_path=None):
        self.llm = None
        self.environment = None
        self.action_lib = None
        self.max_iter = None
        # self.action_lib_description = {}
        # self.action = None
        # self.retrieval_top_k = None
        # self.action_lib_dir = None
        # self.init_action_lib()
        
    # Extract information from text
    def extract_information(self, message, begin_str='[BEGIN]', end_str='[END]'):
        result = []
        _begin = message.find(begin_str)
        _end = message.find(end_str)
        while not (_begin == -1 or _end == -1):
            result.append(message[_begin + len(begin_str):_end].strip())
            message = message[_end + len(end_str):]
            _begin = message.find(begin_str)
            _end = message.find(end_str)
        return result  

    # egular expression to find JSON data within a string
    def extract_json_from_string(self, text):
        # Improved regular expression to find JSON data within a string
        json_regex = r'```json\s*\n\{[\s\S]*?\n\}\s*```'
        
        # Search for JSON data in the text
        matches = re.findall(json_regex, text)

        # Extract and parse the JSON data if found
        if matches:
            # Removing the ```json and ``` from the match to parse it as JSON
            json_data = matches[0].replace('```json', '').replace('```', '').strip()
            try:
                # Parse the JSON data
                parsed_json = json.loads(json_data)
                return parsed_json
            except json.JSONDecodeError as e:
                return f"Error parsing JSON data: {e}"
        else:
            return "No JSON data found in the string."


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
<<<<<<< HEAD
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
=======
                obj_code = self.get_class_source_code(module, class_name)
                self.action_lib.update({class_name: obj_code})
=======
                # get origin code
                source_code = inspect.getsource(module)
                # get class object
                tmp_obj = getattr(module, class_name)() 
                # save origin code
                self.action_lib.update({class_name: source_code})
                # save code description
                self.action_lib_description.update({class_name: tmp_obj.description})
>>>>>>> aaa5bdd (add multi-parameter open_document function)
                
    # get class source code
    # def get_class_source_code(self, module, class_name):
    #     # 获取类对象
    #     tmp_obj = getattr(module, class_name)
    #     print(type(tmp_obj.description))
    #     self.action_lib_description.update({class_name: tmp_obj.description})
    #     # 获取类定义的源文件和行号
    #     source_file = inspect.getsourcefile(tmp_obj)
    #     source_lines, start_line = inspect.getsourcelines(tmp_obj)

    #     # 读取源文件
    #     with open(source_file, 'r') as file:
    #         lines = file.readlines()

    #     # 提取类的源代码
    #     class_code = ''.join(lines[start_line - 1: start_line - 1 + len(source_lines)])

<<<<<<< HEAD
        # 提取类的源代码
        class_code = ''.join(lines[start_line - 1: start_line - 1 + len(source_lines)])

        return class_code
>>>>>>> ac58871 (new example)
=======
    #     return class_code
>>>>>>> aaa5bdd (add multi-parameter open_document function)

if __name__ == '__main__':
<<<<<<< HEAD
    a = BaseAgent()
<<<<<<< HEAD
    a.init_action_lib()
    for k,v in a.action_lib.items():
        print(k)
        print(v())
=======
    # a.init_action_lib()
    # for k,v in a.action_lib.items():
    #     print(k)
    #     print(v)
>>>>>>> ac58871 (new example)
=======
    agent = BaseAgent()
    agent.init_action_lib()
    from jarvis.enviroment.py_env import PythonEnv
    myEnv = PythonEnv()
    # toolName = "execute_sql"
    # res = myEnv.step(a.action_lib['{toolname}'.format(toolname=toolName)]+"\n"+"print({toolname}()())".format(toolname=toolName))
    # print(res.result)
    # print(a.action_lib_description)
    # res = a.action_lib["execute_sql"]()
    # print(res)
    # print(a.action_lib)
    # print(a.action_lib_description)
    for k,v in agent.action_lib.items():
        toolName = k
        toolCode = v
        args = None
        # print(v())
        if(k == "python_interpreter"):
            args = "print('hello world')"
        res = myEnv.step(v+"\n"+"print({toolname}()({args}))".format(toolname=toolName,args=args))
        print(res.result)
        myEnv.reset()
>>>>>>> aaa5bdd (add multi-parameter open_document function)
