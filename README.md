# CV_Project

机器视觉项目《道路车辆多目标实时跟踪系统》

首先系统实现了用户的注册及登录，并且后续的告警将基于登录用户的user_id进行筛选，确保用户只能看到自己的告警信息；其次主要功能为实现道路上车辆的多目标实时跟踪，扩展功能为加入deepseek-v4-flash大语言模型，构建智能驾驶智能体，能够实时/离线分析视频流中的危险情况，并且给出告警，包括以下方面：1.速度；2.碰撞；3.路径预测，并且可以和智能体进行交通方面的对话；最后，将告警记录存储在Mysql关系型数据库中，再进行相关的告警分析。  

主要包含三个部分：  
1.前端文件 driving_agent_web ：采用Vue搭建，主要包含以下页面：注册、登录、实时追踪、智能驾驶、历史告警、告警分析  


2.后端文件 driving_agent ：采用Python搭建，主要包含以下api：智能体deepseek-v4-flash模型api、前端功能实现api、数据库功能实现api  


3.数据库文件 driving_agent_db ：采用Mysql构建，主要包含两张表：用户表users、告警记录表alarm_records  


## 前端页面演示：

注册页面：  
<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/092f4a38-2168-4ad9-9b67-d82a83e0c478" />

登录页面：
<img width="1918" height="912" alt="image" src="https://github.com/user-attachments/assets/6a4fbf56-6537-4467-9b8d-ca1f19fcf5af" />

实时追踪页面：
<img width="1918" height="917" alt="image" src="https://github.com/user-attachments/assets/49a53172-2eb5-432a-b253-0ba996160770" />

智能驾驶&实时预警页面：
<img width="1918" height="921" alt="image" src="https://github.com/user-attachments/assets/b5962730-fb12-46df-a1bb-1c605d7b487a" />

智能驾驶&智能对话页面：
<img width="1918" height="917" alt="image" src="https://github.com/user-attachments/assets/792e95d6-395a-45f5-bff5-c340710f7059" />

历史告警页面：
<img width="1918" height="912" alt="image" src="https://github.com/user-attachments/assets/0031bf1c-80a7-42eb-802b-8a39cad652f2" />

告警分析页面1：
<img width="1918" height="918" alt="image" src="https://github.com/user-attachments/assets/e4c96a22-2f86-48ff-a287-8abc370e83f4" />

告警分析页面2：
<img width="1918" height="917" alt="image" src="https://github.com/user-attachments/assets/bf3250f9-b022-404a-aee8-4874596d3028" />
