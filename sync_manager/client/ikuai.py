import base64
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
from pydantic import BaseModel, Field
import requests
import urllib3
from cachetools import TTLCache
from cachetools import cached
import logging
from django.utils import timezone as django_timezone

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AddPPPUserRequestData(BaseModel):
    """
        添加 PPP 用户请求数据模型
        
        数据示例：
        {
            "username": "test",
            "passwd": "123456112",
            "enabled": "yes",
            "ppptype": "any",
            "bind_ifname": "any",
            "share": "999",
            "auto_mac": "1",
            "upload": 0,
            "download": 0,
            "bind_vlanid": 0,
            "packages": 0,
            "comment": "xxxa1",
            "auto_vlanid": 1,
            "ip_addr": "",
            "mac": "",
            "address": "",
            "name": "xxx",
            "phone": "",
            "cardid": "",
            "ip_type": 0,
            "pppoev6_wan": "",
            "start_time": 1762614055,
            "create_time": "",
            "expires": 1763132476
        }
    """
    # 必填字段
    username: str = Field(description="用户名")
    passwd: str = Field(description="密码")
    
    # 启用状态
    enabled: str = Field(default="yes", description="启用状态：yes 或 no")
    
    # 时间相关字段（Unix 时间戳）
    start_time: int = Field(description="开始时间（Unix 时间戳）", default_factory=lambda: int(django_timezone.now().timestamp()))
    expires: int = Field(default=0, description="过期时间（Unix 时间戳），0为不过期")
    create_time: str = Field(default="", description="创建时间")
    
    # 连接配置
    ppptype: str = Field(default="any", description="PPP 类型")
    bind_ifname: str = Field(default="any", description="绑定接口")
    bind_vlanid: int | str = Field(default=0, description="绑定 VLAN ID")
    auto_vlanid: int = Field(default=1, description="自动 VLAN")
    pppoev6_wan: str = Field(default="", description="PPPoE IPv6 WAN")
    
    # IP 和 MAC 配置
    ip_type: int = Field(default=0, description="IP 类型（0=自动）")
    ip_addr: str = Field(default="", description="IP 地址")
    mac: str = Field(default="", description="MAC 地址")
    auto_mac: int | str = Field(default=1, description="自动 MAC")
    
    # 限制配置
    share: int | str = Field(default=999, description="共享连接数")
    upload: int = Field(default=0, description="上传限速（KB/s）")
    download: int = Field(default=0, description="下载限速（KB/s）")
    packages: int = Field(default=0, description="流量包（字节）")
    
    # 用户信息
    name: str = Field(default="", description="姓名/名称")
    phone: str = Field(default="", description="电话")
    address: str = Field(default="", description="地址")
    comment: str = Field(default="openvpn创建", description="备注")
    
    # 其他字段
    cardid: str = Field(default="", description="卡号")


class EditPPPUserRequestData(BaseModel):
    """
        编辑 PPP 用户请求数据模型

        数据示例：
        {
            "passwd": "test123456",
            "duration": -25412,
            "expires": 1762627484,
            "start_time": 1762541072,
            "create_time": 1762541096,
            "ppptype": "any",
            "cardid": "",
            "pppname": "",
            "last_offtime": 1762586779,
            "share": 1,
            "auto_mac": 1,
            "upload": 0,
            "download": 0,
            "ip_type": 0,
            "ip_addr": "10.100.250.5",
            "mac": "",
            "address": "",
            "name": "XXX",
            "last_conntime": 0,
            "phone": "",
            "packages": 0,
            "proxy_username": "",
            "pppoev6_wan": "",
            "auto_vlanid": 1,
            "bind_vlanid": "0",
            "bind_ifname": "any",
            "id": 2,
            "enabled": "yes",
            "comment": "remark",
            "username": "test"
        }
    """
    # 必填字段
    id: int = Field(description="账号ID")
    username: str = Field(description="用户名")
    passwd: str = Field(description="密码")
    expires: int = Field(description="过期时间（Unix 时间戳），0为不过期",default=0)
    start_time: int = Field(description="开始时间（Unix 时间戳）",default_factory=lambda: int(django_timezone.now().timestamp()))
    
    # 启用状态
    enabled: str = Field(default="yes", description="启用状态：yes 或 no")
    
    # 时间相关字段（Unix 时间戳）
    create_time: int = Field(default=0, description="创建时间")
    last_conntime: int = Field(default=0, description="最后连接时间")
    last_offtime: int = Field(default=0, description="最后离线时间")
    duration: int = Field(default=0, description="在线时长（秒）")
    
    # 连接配置
    ppptype: str = Field(default="any", description="PPP 类型")
    pppname: str = Field(default="", description="PPP 名称")
    bind_ifname: str = Field(default="any", description="绑定接口")
    bind_vlanid: str = Field(default="0", description="绑定 VLAN ID")
    auto_vlanid: int = Field(default=1, description="自动 VLAN")
    pppoev6_wan: str = Field(default="", description="PPPoE IPv6 WAN")
    
    # IP 和 MAC 配置
    ip_type: int = Field(default=0, description="IP 类型（0=自动）")
    ip_addr: str = Field(default="", description="IP 地址")
    mac: str = Field(default="", description="MAC 地址")
    auto_mac: int = Field(default=1, description="自动 MAC")
    
    # 限制配置
    share: int = Field(default=999, description="共享连接数")
    upload: int = Field(default=0, description="上传限速（KB/s）")
    download: int = Field(default=0, description="下载限速（KB/s）")
    packages: int = Field(default=0, description="流量包（字节）")
    
    # 用户信息
    name: str = Field(default="", description="姓名/名称")
    phone: str = Field(default="", description="电话")
    address: str = Field(default="", description="地址")
    comment: str = Field(default="openvpn创建", description="备注")
    
    # 其他字段
    cardid: str = Field(default="", description="卡号")
    proxy_username: str = Field(default="", description="代理用户名")

    

class IKuaiAPIClient:
    """iKuai API 客户端"""
    FIXED_SALT = "salt_11"
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.LOGIN_URL = f"{self.base_url}/Action/login"
        self.username = username
        self.password = password
        self.session = requests.Session()
    
    def login(self):
        """登录 iKuai 系统获取 token"""
        HEADERS = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/login",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        
        try:
            self.session.headers.update(HEADERS)
            self.session.cookies.set("username", self.username)
            self.session.cookies.set("sess_key", "")
            payload = self.build_payload(self.username, self.password)
            response = self.session.post(self.LOGIN_URL, json=payload, verify=False, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('Result') == 10000:
                logger.info('Successfully logged in to iKuai')
                return True
            else:
                logger.error(f'iKuai login failed: {data.get("ErrMsg")}')
                return False
        except Exception as e:
            logger.error(f'iKuai login error: {str(e)}')
            return False

    def create_account(self, username, password, expires_days=30, **kwargs) -> int:
        """
        创建 OpenVPN 账号
        
        Args:
            username: VPN账号用户名
            password: VPN账号密码
            expires_days: 账号有效期（天），0为不过期
            **kwargs: 其他可选参数
        """
        if not self.login():
            raise Exception('Failed to login to iKuai')
        
        now = int(django_timezone.now().timestamp())
        expires = int((django_timezone.now() + timedelta(days=expires_days)).timestamp()) if expires_days > 0 else 0
        
        # 使用 Pydantic 模型构建数据
        request_data = AddPPPUserRequestData(
            username=username,
            passwd=password,
            start_time=kwargs.get('start_time', now),
            expires=kwargs.get('expires', expires),
            ppptype=kwargs.get('ppptype', 'any'),
            bind_ifname=kwargs.get('bind_ifname', 'any'),
            bind_vlanid=kwargs.get('bind_vlanid', 0),
            auto_vlanid=kwargs.get('auto_vlanid', 1),
            share=kwargs.get('share', 999),
            upload=kwargs.get('upload', 0),
            download=kwargs.get('download', 0),
            ip_type=kwargs.get('ip_type', 0),
            auto_mac=kwargs.get('auto_mac', 1),
            name=kwargs.get('name', ''),
        )
        
        data = request_data.model_dump()
        
        try:
            response = self.session.post(
                f'{self.base_url}/Action/call',
                json={
                    'action': 'add',
                    'func_name': 'pppuser',
                    'param': data
                },
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('Result') == 30000:
                logger.info(f'Successfully created account: {username}')
                return int(result.get('RowId'))
            else:
                error_msg = result.get('ErrMsg', 'Unknown error')
                logger.error(f'Failed to create account {username}: {error_msg}')
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f'Error creating account {username}: {str(e)}')
            raise
    
    def get_account(self, username):
        """获取账号信息"""
        if not self.login():
            raise Exception('Failed to login to iKuai')
        
        accounts = self.list_accounts()
        for account in accounts:
            if account.get('username') == username:
                return account
        return None
    
    def _list_accounts(self,index,end_index):
        response = self.session.post(
                f'{self.base_url}/Action/call',
                json={
                    'action': 'show',
                    'func_name': 'pppuser',
                    'param': {
                    "TYPE": "total,data",
                    "limit": f"{index},{end_index}",
                    "ORDER_BY": "",
                    "ORDER": "",
                    "FINDS": "username,name,address,phone,comment",
                    "KEYWORDS": "",
                    "FILTER1": "",
                    "FILTER2": "",
                    "FILTER3": "",
                    "FILTER4": "",
                    "FILTER5": ""
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get('Result') == 30000:
            accounts = result.get('Data', {}).get('data', [])
            total = result.get('Data', {}).get('total', 0)
            return accounts,total
        else:
            error_msg = result.get('ErrMsg', 'Unknown error')
            logger.error(f'Failed to list accounts: {error_msg}')
            raise Exception(error_msg)
    
    @cached(TTLCache(maxsize=150, ttl=5))
    def list_accounts(self):
        """列出所有账号"""
        if not self.login():
            raise Exception('Failed to login to iKuai')
        
        try:
            _index = 0
            _end_index = 100
            all_accounts = []
            total = 0  # Initialize total before the loop
            while True:
                accounts, total = self._list_accounts(_index,_end_index)
                if accounts:
                    all_accounts.extend(accounts)
                _index += _end_index + 1
                _end_index = _index + 100
                if _index + 1 > total:
                    # 下一轮索引超出总数，结束循环
                    break
            return all_accounts
        except Exception as e:
            logger.error(f'Error listing accounts: {str(e)}')
            raise e

    def update_account(self, account_id, params: EditPPPUserRequestData):
        """更新账号信息"""
        if not self.login():
            raise Exception('Failed to login to iKuai')
        params.id = account_id
        data = params.model_dump()
        try:
            response = self.session.post(
                f'{self.base_url}/Action/call',
                json={
                    'action': 'edit',
                    'func_name': 'pppuser',
                    'param': data
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('Result') == 30000:
                logger.info(f'Successfully updated account ID: {account_id}')
                return
            else:
                error_msg = result.get('ErrMsg', 'Unknown error')
                logger.error(f'Failed to update account {account_id}: {error_msg}')
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f'Error updating account {account_id}: {str(e)}')
            raise
    
    def delete_account(self, account_id):
        """删除账号"""
        if not self.login():
            raise Exception('Failed to login to iKuai')
        
        try:
            response = self.session.post(
                f'{self.base_url}/Action/call',
                json={
                    'action': 'del',
                    'func_name': 'pppuser',
                    'param': {'id': str(account_id)}
                }
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('Result') == 30000:
                logger.info(f'Successfully deleted account ID: {account_id}')
                return True
            else:
                error_msg = result.get('ErrMsg', 'Unknown error')
                logger.error(f'Failed to delete account {account_id}: {error_msg}')
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f'Error deleting account {account_id}: {str(e)}')
            raise

    def md5_hex(self, s: str) -> str:
        return hashlib.md5(s.encode("utf-8")).hexdigest()

    def build_payload(self, username: str, password: str):
        pass_raw = self.FIXED_SALT + password
        pass_b64 = base64.b64encode(pass_raw.encode()).decode()
        passwd_hex = self.md5_hex(password)   # NOTE: md5 of plain password
        return {
            "username": username,
            "passwd": passwd_hex,
            "pass": pass_b64,
            "remember_password": "true"
        }





