import re
import ipaddress
import logging

from django.conf import settings

from framarama.base.utils import Filesystem, Process, DateTime


logger = logging.getLogger(__name__)


class Capability:

    def _noop(self):
        return

    def _false(self):
        return False

    def _true(self):
        return True

    def _none(self):
        return None

    def _list(self):
        return []

    def _dict(self):
        return {}

    def display_off(self):
        self._noop()

    def display_on(self):
        self._noop()

    def display_status(self):
        return self._true()

    def display_size(self):
        return self._none()

    def mem_total(self):
        return self._none()

    def mem_free(self):
        return self._none()

    def sys_uptime(self):
        return self._none()

    def cpu_temp(self):
        return self._none()

    def cpu_load(self):
        return self._none()

    def disk_data_free(self):
        return self._none()

    def disk_tmp_free(self):
        return self._none()

    def sys_uptime(self):
        return self._none()

    def net_config(self):
        return self._none()

    def net_toggle_ap(self):
        return self._none()

    def net_wifi_list(self):
        return self._dict()

    def net_profile_list(self):
        return self._list()

    def net_profile_save(self):
        return self._none()

    def net_profile_delete(self):
        return self._none()

    def app_log(self):
        return self._none()

    def app_restart(self):
        return self._none()

    def app_shutdown(self):
        return self._none()

    def app_revision(self):
        return self._none()

    def app_check(self):
        return self._none()

    def app_update(self):
        return self._none()


class Capabilities:

    @staticmethod
    def discover():
        _capability = Capability()
        if Process.exec_search('vcgencmd'):  # Raspberry PIs
            _capability.display_on = Capabilities.vcgencmd_display_on
            _capability.display_off = Capabilities.vcgencmd_display_off
            _capability.display_status = Capabilities.vcgencmd_display_status
        elif Process.exec_search('xrandr'):
            _capability.display_on = Capabilities.xrandr_display_on
            _capability.display_off = Capabilities.xrandr_display_off
            _capability.display_status = Capabilities.xrandr_display_status
        if Process.exec_search('xrandr'):
            _capability.display_size = Capabilities.xrandr_display_size
        if Filesystem.file_exists('/proc/meminfo'):
            _capability.mem_total = Capabilities.read_meminfo_total
            _capability.mem_free = Capabilities.read_meminfo_free
        if Filesystem.file_exists('/proc/uptime'):
            _capability.sys_uptime = Capabilities.read_uptime
        if Process.exec_search('uptime'):
            _capability.cpu_load = Capabilities.uptime_loadavg
        if Filesystem.file_exists('/sys/class/thermal/thermal_zone0/temp'):
            _capability.cpu_temp = Capabilities.read_thermal
        if Process.exec_search('df'):
            _capability.disk_data_free = Capabilities.df_data
            _capability.disk_tmp_free = Capabilities.df_tmp
        if Process.exec_search('ip'):
            _capability.net_config = Capabilities.ip_netcfg
        if Process.exec_search('nmcli'):
            _capability.net_toggle_ap = Capabilities.nmcli_toggle_ap
            _capability.net_wifi_list = Capabilities.nmcli_wifi_list
            _capability.net_profile_list = Capabilities.nmcli_profile_list
            _capability.net_profile_save = Capabilities.nmcli_profile_save
            _capability.net_profile_delete = Capabilities.nmcli_profile_delete
            _capability.net_profile_connect = Capabilities.nmcli_profile_connect
        if Process.exec_run(['sudo', '-n', 'systemctl', 'show', 'framarama'], sudo=True):
            _capability.app_log = Capabilities.app_log_systemd
            _capability.app_restart = Capabilities.app_restart_systemd
        if Process.exec_search('shutdown'):
            _capability.app_shutdown = Capabilities.app_shutdown
        if Process.exec_search('git'):
            _capability.app_revision = Capabilities.app_revision
            _capability.app_check = Capabilities.app_check
            _capability.app_update = Capabilities.app_update
        return _capability

    def vcgencmd_display_on():
        Process.exec_run(['vcgencmd', 'display_power', '1'])

    def vcgencmd_display_off():
        Process.exec_run(['vcgencmd', 'display_power', '0'])

    def vcgencmd_display_status():
        _status = Process.exec_run(['vcgencmd', 'display_power'])
        return _status is None or _status == b'display_power=1\n'

    def _xrandr_display_name():
        _name = None
        _status = True
        _xrandr = Process.exec_run(['xrandr'])
        if _xrandr:
            _lines = _xrandr.split(b'\n')
            # HDMI-1 connected primary 1280x800+0+0 (normal left inverted right x axis y axis) 337mm x 270mm
            _connected = [_line for _line in _lines if b'connected' in _line]
            if len(_connected):
                _name = _connected[0].split(b' ')[0]
            #    1280x800      59.81*+
            _size = [_line for _line in _lines if b'x' in _line and b'.' in _line]
            if len(_size):
                _status = len([_line for _line in _size if b'*' in _line]) > 0
        return (_name, _status)

    def xrandr_display_on():
        (_name, _status) = Capabilities._xrandr_display_name()
        if _name:
            Process.exec_run(['xrandr', '--output', _name, '--auto'])

    def xrandr_display_off():
        (_name, _status) = Capabilities._xrandr_display_name()
        if _name:
            Process.exec_run(['xrandr', '--output', _name, '--off'])

    def xrandr_display_status():
        (_name, _status) = Capabilities._xrandr_display_name()
        return _status

    def xrandr_display_size():
        _xrandr = Process.exec_run(['xrandr'])
        if _xrandr:
            # Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 16384 x 16384
            for _resolution in _xrandr.split(b'\n')[0].split(b','):
                if b'current' in _resolution:
                    _values = _resolution.strip().split(b' ')
                    return (int(_values[1]), int(_values[3]))
        return None

    def _read_meminfo(fields=None):
        _lines = Filesystem.file_read('/proc/meminfo')
        _lines = [_line for _line in _lines.split(b'\n') if _line] if _lines else []
        _lines = [_line.split() for _line in _lines]
        _info = {_line[0].decode().strip(':'): _line[1].decode() for _line in _lines}
        if fields:
            return tuple([_info.get(_field) for _field in fields])
        else:
            return _info

    def read_meminfo_total():
        _mem_total, = Capabilities._read_meminfo(['MemTotal'])
        return int(_mem_total) if _mem_total else None

    def read_meminfo_free():
        _mem_free, _mem_cached = Capabilities._read_meminfo(['MemFree', 'Cached'])
        return int(_mem_free) + int(_mem_cached) if _mem_free else None

    def read_uptime():
        _info = Filesystem.file_read('/proc/uptime')
        return float(_info.split(b'.')[0]) if _info else None

    def _df(partition):
        _info = Process.exec_run(['df', '-k', partition])
        _info = _info.split() if _info else None
        return (float(_info[-4]), float(_info[-3])) if _info else None

    def df_data():
        return Capabilities._df(settings.FRAMARAMA['DATA_PATH'])

    def df_tmp():
        return Capabilities._df('/tmp')

    def uptime_loadavg():
        _info = Process.exec_run(['uptime'])
        return float(_info.split()[-3].rstrip(b',')) if _info else None

    def read_thermal():
        _info = Filesystem.file_read('/sys/class/thermal/thermal_zone0/temp')
        return int(float(_info)/1000) if _info else None

    def ip_netcfg():
        _info = Process.exec_run(['ip', 'route'])
        _info = [_line.decode() for _line in _info.split(b'\n') if _line.startswith(b'default via')] if _info else []
        _info = [_line.split() for _line in _info][0] if _info else None
        _gateway = _info[2] if _info and len(_info) > 1 else None
        _device = _info[4] if _info and len(_info) > 3 else None
        _dhcp = (_info[6] == 'dhcp') if _info and len(_info) > 5 else None

        _info = Process.exec_run(['ip', 'a', 'show', 'dev', _device]) if _device else ''
        _info = [_line.decode().split() for _line in _info.split(b'\n')] if _info else []
        _mac = None
        _ipv4 = []
        _ipv6 = []
        for _line in [_line for _line in _info if _line]:
            if _line[0].startswith('link'):
                _mac = _line[1]
            elif _line[0] == 'inet':
                _ipv4.append(_line[1])
            elif _line[0] == 'inet6':
                _ipv6.append(_line[1])
        _gw_ip = ipaddress.ip_address(_gateway) if _gateway else None
        _ip = [_ip.split('/')[0] for _ip in _ipv4 + _ipv6 if _gw_ip in ipaddress.ip_network(_ip, strict=False)]

        return {
            'gateway': _gateway,
            'device': _device,
            'mac': _mac,
            'ip': _ip,
            'ipv4': _ipv4,
            'ipv6': _ipv6,
            'mode': 'DHCP' if _dhcp else 'static'
        }

    def nmcli_profile_list():
        _profiles = {}
        # NAME       UUID                                  TYPE  DEVICE  ACTIVE
        # NetName1   93dba0ab-4cd6-4c0f-b790-2c5689f8686b  wifi  wlan0   yes
        # NetName2   909c4d81-4211-4810-9f98-32f74f43906a  wifi  --      no
        _profile_list = Process.exec_run(['nmcli', '--fields', 'NAME,UUID,TYPE,DEVICE,ACTIVE', 'connection', 'show'])
        if _profile_list:
            _profile_list = _profile_list.decode().split('\n')
            _columns = _profile_list.pop(0).lower().split()
            for _parts in [_line.split() for _line in _profile_list]:
                if len(_parts) == 0:
                    continue
                _i = 0
                _profile = {}
                for _column in _columns:
                    _value = _parts[_i]
                    if _column == 'active':
                        _value = True if _value == 'yes' else False
                    _profile[_column] = _value
                    _i = _i + 1
                _profiles[_profile['name']] = _profile
        return _profiles

    def nmcli_ap_active(profiles):
        return 'framarama' in profiles and profiles['framarama']['active']

    def nmcli_profile_save(name, password):
        if name is None or name == '' or password is None or password == '':
            return
        _profiles = Capabilities.nmcli_profile_list(device, *args, **kwargs)
        _args = ['sudo', 'nmcli', 'connection']
        if name in _profiles:
            _args.extend(['modify', name])
            _args.extend(['802-11-wireless-security.psk', password])
            logger.info("Updating network {}".format(name))
        else:
            _args.extend(['add'])
            _args.extend(['connection.id', name])
            _args.extend(['connection.type', '802-11-wireless'])
            _args.extend(['connection.autoconnect', '1'])
            _args.extend(['802-11-wireless.ssid', name])
            _args.extend(['802-11-wireless-security.key-mgmt', 'wpa-psk'])
            _args.extend(['802-11-wireless-security.psk', password])
            logger.info("Adding network {}".format(name))
        Process.exec_run(_args, sudo=True)

    def nmcli_profile_delete(name):
        if name is None or name == '':
            return
        _profiles = Capabilities.nmcli_profile_list()
        if name not in _profiles or _profiles[name]['active']:
            return
        logger.info("Deleting network {}".format(name))
        Process.exec_run(['sudo', 'nmcli', 'connection', 'delete', name], sudo=True)

    def nmcli_profile_connect(name):
        if name is None or name == '':
            return
        _profiles = Capabilities.nmcli_profile_list()
        if name not in _profiles:
            return
        _wifi_list = Capabilities.nmcli_wifi_list()
        if name not in _wifi_list:
            return
        logger.info("Connecting network {}".format(name))
        Process.exec_run(['sudo', 'nmcli', 'connection', 'up', name], sudo=True)

    def nmcli_wifi_list():
        _networks = {}
        # IN-USE  BSSID              SSID          MODE   CHAN  RATE        SIGNAL  BARS  SECURITY
        # *       XX:XX:XX:XX:XX:XX  NetworkName   Infra  6     130 Mbit/s  46      ▂▄__  WPA1 WPA2
        _wifi_list = Process.exec_run(['sudo', 'nmcli', 'device', 'wifi', 'list', '--rescan', 'yes'], sudo=True)
        if _wifi_list:
            _wifi_list = _wifi_list.decode().split('\n')
            _columns = _wifi_list.pop(0).lower().split()
            for _parts in [_line.split() for _line in _wifi_list]:
                if len(_parts) == 0:
                    continue
                _network = {'active': _parts[0] == '*'}
                if _network['active']:
                    _parts.pop(0)
                _i = 0
                for _column in _columns:
                    if 'use' in _column:  # skip in-use column, already checked
                        continue
                    elif 'rate' in _column:
                        _network[_column] = _parts[_i] + ' ' + _parts[_i+1]
                        _i = _i + 1
                    else:
                        _network[_column] = _parts[_i]
                    _i = _i + 1
                if _network['ssid'] != 'framaRAMA':
                    _networks[_network['ssid']] = _network
        return _networks

    def nmcli_toggle_ap():
        _profiles = Capabilities.nmcli_profile_list(device, *args, **kwargs)
        if not Capabilities.nmcli_ap_active(_profiles):
            logger.info("Activating Access Point.")
            if 'framarama' not in _profiles:
                Process.exec_run(['sudo', '-n', 'nmcli', 'device', 'wifi', 'hotspot', 'con-name', 'framarama', 'ssid', 'framaRAMA', 'password', 'framarama', 'band', 'bg'], sudo=True)
            else:
                Process.exec_run(['sudo', '-n', 'nmcli', 'connection', 'up', 'framarama'], sudo=True)
        else:
            logger.info("Deactivating Access Point.")
            Process.exec_run(['sudo', '-n', 'nmcli', 'connection', 'delete', 'framarama'], sudo=True)

    def app_log_systemd():
        return Process.exec_run(['sudo', '-n', 'systemctl', 'status', '-n', '100', 'framarama'], sudo=True)

    def app_restart_systemd():
        return Process.exec_run(['sudo', '-n', 'systemctl', 'restart', 'framarama'], sudo=True)

    def app_shutdown():
        return Process.exec_run(['sudo', 'shutdown', '-h', 'now'], sudo=True)

    def _git_remotes():
        _remotes = Process.exec_run(['git', 'remote', '-v'])
        _remotes = [_line.split() for _line in _remotes.decode().split('\n') if len(_line)] if _remotes else []
        _remotes = {_parts[0]: _parts[1] for _parts in _remotes if _parts[-1] == '(fetch)'}
        return _remotes

    def _git_revisions():
        _revisions = []
        _out = Process.exec_run(['git', 'tag', '-l', '--sort=-v:refname'])
        if _out:
            _out = [_line for _line in _out.decode().split('\n')]
            _revisions.extend(_out)
        _revisions.append('master')
        #_out = Process.exec_run(['git', 'branch', '-r'])
        #if _out:
        #    _out = [_line.strip() for _line in _out.decode().split('\n')]
        #    _revisions.extend(_out)
        return [_rev for _rev in _revisions if len(_rev)]

    def _git_current_ref(refs):
        if 'HEAD' in refs:
            refs.remove('HEAD')
        return refs[0] if len(refs) else None

    def _git_log(args):
        _remote = settings.FRAMARAMA['GIT_REMOTE']
        _args = ['git', 'log', '--pretty=format:%h %aI %d %s', '--decorate']
        _args.extend(args)
        _log = Process.exec_run(_args)
        _logs = []
        for _line in [_line for _line in _log.decode().split("\n")] if _log else []:
            # de4a83b 2022-12-17T11:14:06+01:00  (HEAD, tag: v0.2.0) Implement frontend capability to retrieve display size (using xrandr)
            # 7034857 2023-01-07T11:42:25+01:00  (HEAD -> master) Silent sudo check command execution in Process.exec_run()
            _commit, _date, _values = _line.split(maxsplit=2)
            _refs, _comment = _values[1:].split(') ', maxsplit=1)
            _refs = [_ref.strip() for _ref in _refs.split(',')]       # separate tags
            _refs = [_ref.replace('HEAD -> ', '') for _ref in _refs]  # remove HEAD pointer
            _refs = [_ref.replace('tag: ', '') for _ref in _refs]     # remove tag: prefix
            _refs = [_ref.replace(_remote+'/', '') for _ref in _refs] # remove remote name
            _refs = [_ref for _ref in _refs if '/' not in _ref]       # remove remote branches
            _refs = [_ref for _ref in _refs if _ref not in ['HEAD']]  # remove special names (HEAD)
            _logs.append({
                'hash': _commit,
                'date': DateTime.parse(_date),
                'comment': _comment,
                'refs': _refs
            })
        return _logs

    def app_revision():
        _logs = Capabilities._git_log(['-1'])
        if _logs:
            _remote = settings.FRAMARAMA['GIT_REMOTE']
            _branch = Process.exec_run(['git', 'branch', '--show-current'])
            _branch = _branch.decode().strip() if _branch else None
            _revisions = Capabilities._git_revisions()
            if _branch == 'master':
                _logs_update = Capabilities._git_log(['-1', '{0}..{1}/{0}'.format(_branch, _remote)])
                _update_ref = _branch
            elif len(_revisions):
                _logs_update = Capabilities._git_log(['-1', '{0}..{1}'.format(_branch, _revisions[0])])
                _update_ref = _revisions[0]
            else:
                _logs_update = None
                _update_ref = None
            _rev = _logs[0]
            _rev.update({
                'branch': _branch,
                'remote': {'name': _remote, 'url': Capabilities._git_remotes()[_remote]},
                'revisions': _revisions,
                'current': Capabilities._git_current_ref(_rev['refs']),
                'update': _logs_update[0]|{'ref':_update_ref} if _logs_update else None
            })
            return _rev
        return None

    def app_check(url=None, username=None, password=None):
        _remote = settings.FRAMARAMA['GIT_REMOTE']
        _remotes = Capabilities._git_remotes()
        _url = url if url else _remotes[_remote]
        _username_pattern = r'^(.*://)([^@]+@)?(.*)'
        if username is not None:
            _url = re.sub(_username_pattern, '\\1' + re.escape(username) + '@\\3', _url)
        else:
            _url = re.sub(_username_pattern, '\\1\\3', _url)
        logger.info("Check version update from {} using {} ...".format(_remote, _url))
        if _remote in _remotes:
            logger.info("Update remote {} to {}".format(_remote, _url))
            _remote_update = Process.exec_run(['git', 'remote', 'set-url', _remote, _url])
        else:
            logger.info("Adding remote {} to {}".format(_remote, _url))
            _remote_update = Process.exec_run(['git', 'remote', 'add', _remote, _url])
        if _remote_update is None:
            logger.error("Can not setup remote {} with {}".format(_remote, _url))
            return
        _fetch = Process.exec_run(['git', 'fetch', _remote], env={
            'GIT_ASKPASS': settings.BASE_DIR / 'docs' / 'git' / 'git-ask-pass.sh' ,
            'GIT_PASSWORD': password if password is not None else '',
        })
        if _fetch is None:
            logger.error("Can not fetch updates!")
        else:
            logger.info("Updates fetched!")
        Process.exec_run(['git', 'remote', 'set-url', _remote, url])

    def app_update(revision):
        _remote = settings.FRAMARAMA['GIT_REMOTE']
        logger.info("Check version update ...")
        _revisions = Capabilities._git_revisions()
        if revision not in _revisions:
            logger.error("Can not update to non-existant revision {}".format(revision))
            return
        _stash = Process.exec_run(['git', 'stash'])
        if _stash is None:
            logger.error("Can not stash changes!")
            return
        logger.info("Changes stashed!")
        if revision == 'master':
            _update = Process.exec_run(['git', 'merge', '--ff-only', '{}/{}'.format(_remote, revision)])
        else:
            _update = Process.exec_run(['git', 'checkout', revision])
        if _update is None:
            logger.error("Can not checkout revision!")
        else:
            logger.info("Revision checked out!")
        _pop = Process.exec_run(['git', 'stash', 'pop'])
        if _pop is None:
            logger.error("Can not pop stash again!")
        Capabilities.app_restart_systemd()

