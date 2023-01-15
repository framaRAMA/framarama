import ipaddress
import logging

from django.conf import settings

from framarama.base.utils import Filesystem, Process, DateTime


logger = logging.getLogger(__name__)


class Capability:
    DISPLAY_OFF = 'display.off'
    DISPLAY_ON = 'display.on'
    DISPLAY_STATUS = 'display.status'
    DISPLAY_SIZE = 'display.size'
    MEM_TOTAL = 'memory.total'
    MEM_FREE = 'memory.free'
    DISK_DATA_FREE = 'disk.data.free'
    DISK_TMP_FREE = 'disk.tmp.free'
    SYS_UPTIME = 'system.uptime'
    CPU_LOAD = 'cpu.load'
    CPU_TEMP = 'cpu.temp'
    NET_CONFIG = 'network.config'
    NET_TOGGLE_AP = 'network.toggle.ap'
    NET_WIFI_LIST = 'network.wifi.list'
    NET_PROFILE_LIST = 'network.profile.list'
    NET_PROFILE_SAVE = 'network.profile.save'
    NET_PROFILE_DELETE = 'network.profile.delete'
    NET_PROFILE_CONNECT = 'network.profile.connect'
    APP_LOG = 'app.log'
    APP_RESTART = 'app.restart'
    APP_SHUTDOWN = 'app.shutdown'
    APP_REVISION = 'app.revision'
    APP_CHECK = 'app.check'
    APP_UPDATE = 'app.update'


    @staticmethod
    def discover():
        _capabilities = {
            Capability.DISPLAY_ON: Capability.noop,
            Capability.DISPLAY_OFF: Capability.noop,
            Capability.DISPLAY_STATUS: Capability.return_true,
            Capability.DISPLAY_SIZE: Capability.return_none,
            Capability.MEM_TOTAL: Capability.return_none,
            Capability.MEM_FREE: Capability.return_none,
            Capability.SYS_UPTIME: Capability.return_none,
            Capability.CPU_TEMP: Capability.return_none,
            Capability.CPU_LOAD: Capability.return_none,
            Capability.DISK_DATA_FREE: Capability.return_none,
            Capability.DISK_TMP_FREE: Capability.return_none,
            Capability.NET_CONFIG: Capability.return_none,
            Capability.NET_TOGGLE_AP: Capability.return_none,
            Capability.NET_WIFI_LIST: Capability.return_dict,
            Capability.NET_PROFILE_LIST: Capability.return_list,
            Capability.NET_PROFILE_SAVE: Capability.return_none,
            Capability.NET_PROFILE_DELETE: Capability.return_none,
            Capability.APP_LOG: Capability.return_none,
            Capability.APP_RESTART: Capability.return_none,
            Capability.APP_SHUTDOWN: Capability.return_none,
            Capability.APP_REVISION: Capability.return_none,
            Capability.APP_CHECK: Capability.return_none,
            Capability.APP_UPDATE: Capability.return_none,
        }
        if Process.exec_search('vcgencmd'):  # Raspberry PIs
            _capabilities[Capability.DISPLAY_ON] = Capability.vcgencmd_display_on
            _capabilities[Capability.DISPLAY_OFF] = Capability.vcgencmd_display_off
            _capabilities[Capability.DISPLAY_STATUS] = Capability.vcgencmd_display_status
        elif Process.exec_search('xrandr'):
            _capabilities[Capability.DISPLAY_ON] = Capability.xrandr_display_on
            _capabilities[Capability.DISPLAY_OFF] = Capability.xrandr_display_off
            _capabilities[Capability.DISPLAY_STATUS] = Capability.xrandr_display_status
        if Process.exec_search('xrandr'):
            _capabilities[Capability.DISPLAY_SIZE] = Capability.xrandr_display_size
        if Filesystem.file_exists('/proc/meminfo'):
            _capabilities[Capability.MEM_TOTAL] = Capability.read_meminfo_total
            _capabilities[Capability.MEM_FREE] = Capability.read_meminfo_free
        if Filesystem.file_exists('/proc/uptime'):
            _capabilities[Capability.SYS_UPTIME] = Capability.read_uptime
        if Process.exec_search('uptime'):
            _capabilities[Capability.CPU_LOAD] = Capability.uptime_loadavg
        if Filesystem.file_exists('/sys/class/thermal/thermal_zone0/temp'):
            _capabilities[Capability.CPU_TEMP] = Capability.read_thermal
        if Process.exec_search('df'):
            _capabilities[Capability.DISK_DATA_FREE] = Capability.df_data
            _capabilities[Capability.DISK_TMP_FREE] = Capability.df_tmp
        if Process.exec_search('ip'):
            _capabilities[Capability.NET_CONFIG] = Capability.ip_netcfg
        if Process.exec_search('nmcli'):
            _capabilities[Capability.NET_TOGGLE_AP] = Capability.nmcli_toggle_ap
            _capabilities[Capability.NET_WIFI_LIST] = Capability.nmcli_wifi_list
            _capabilities[Capability.NET_PROFILE_LIST] = Capability.nmcli_profile_list
            _capabilities[Capability.NET_PROFILE_SAVE] = Capability.nmcli_profile_save
            _capabilities[Capability.NET_PROFILE_DELETE] = Capability.nmcli_profile_delete
            _capabilities[Capability.NET_PROFILE_CONNECT] = Capability.nmcli_profile_connect
        if Process.exec_run(['sudo', '-n', 'systemctl', 'show', 'framarama'], sudo=True):
            _capabilities[Capability.APP_LOG] = Capability.app_log_systemd
            _capabilities[Capability.APP_RESTART] = Capability.app_restart_systemd
        if Process.exec_search('shutdown'):
            _capabilities[Capability.APP_SHUTDOWN] = Capability.app_shutdown
        if Process.exec_search('git'):
            _capabilities[Capability.APP_REVISION] = Capability.app_revision
            _capabilities[Capability.APP_CHECK] = Capability.app_check
            _capabilities[Capability.APP_UPDATE] = Capability.app_update
        return _capabilities

    def noop(device, *args, **kwargs):
        return

    def return_false(device, *args, **kwargs):
        return False

    def return_true(device, *args, **kwargs):
        return True

    def return_none(device, *args, **kwargs):
        return None

    def return_list(device, *args, **kwargs):
        return []

    def return_dict(device, *args, **kwargs):
        return {}

    def vcgencmd_display_on(device, *args, **kwargs):
        Process.exec_run(['vcgencmd', 'display_power', '1'])

    def vcgencmd_display_off(device, *args, **kwargs):
        Process.exec_run(['vcgencmd', 'display_power', '0'])

    def vcgencmd_display_status(device, *args, **kwargs):
        return Process.exec_run(['vcgencmd', 'display_power']) == b'display_power=1\n'

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

    def xrandr_display_on(device, *args, **kwargs):
        (_name, _status) = Capability._xrandr_display_name()
        if _name:
            Process.exec_run(['xrandr', '--output', _name, '--auto'])

    def xrandr_display_off(device, *args, **kwargs):
        (_name, _status) = Capability._xrandr_display_name()
        if _name:
            Process.exec_run(['xrandr', '--output', _name, '--off'])

    def xrandr_display_status(device, *args, **kwargs):
        (_name, _status) = Capability._xrandr_display_name()
        return _status

    def xrandr_display_size(device, *args, **kwargs):
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

    def read_meminfo_total(device, *args, **kwargs):
        _mem_total, = Capability._read_meminfo(['MemTotal'])
        return int(_mem_total) if _mem_total else None

    def read_meminfo_free(device, *args, **kwargs):
        _mem_free, _mem_cached = Capability._read_meminfo(['MemFree', 'Cached'])
        return int(_mem_free) + int(_mem_cached) if _mem_free else None

    def read_uptime(device, *args, **kwargs):
        _info = Filesystem.file_read('/proc/uptime')
        return float(_info.split(b'.')[0]) if _info else None

    def _df(partition):
        _info = Process.exec_run(['df', '-k', partition])
        _info = _info.split() if _info else None
        return (int(_info[-4]), int(_info[-3])) if _info else None

    def df_data(device, *args, **kwargs):
        return Capability._df(settings.FRAMARAMA['DATA_PATH'])

    def df_tmp(device, *args, **kwargs):
        return Capability._df('/tmp')

    def uptime_loadavg(device, *args, **kwargs):
        _info = Process.exec_run(['uptime'])
        return float(_info.split()[-3].rstrip(b',')) if _info else None

    def read_thermal(device, *args, **kwargs):
        _info = Filesystem.file_read('/sys/class/thermal/thermal_zone0/temp')
        return int(float(_info)/1000) if _info else None

    def ip_netcfg(device, *args, **kwargs):
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

    def nmcli_profile_list(device, *args, **kwargs):
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

    def nmcli_profile_save(device, name, password, *args, **kwargs):
        if name is None or name == '' or password is None or password == '':
            return
        _profiles = Capability.nmcli_profile_list(device, *args, **kwargs)
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

    def nmcli_profile_delete(device, name, *args, **kwargs):
        if name is None or name == '':
            return
        _profiles = Capability.nmcli_profile_list(device, *args, **kwargs)
        if name not in _profiles or _profiles[name]['active']:
            return
        logger.info("Deleting network {}".format(name))
        Process.exec_run(['sudo', 'nmcli', 'connection', 'delete', name], sudo=True)

    def nmcli_profile_connect(device, name, *args, **kwargs):
        if name is None or name == '':
            return
        _profiles = Capability.nmcli_profile_list(device, *args, **kwargs)
        if name not in _profiles:
            return
        _wifi_list = Capability.nmcli_wifi_list(device, *args, **kwargs)
        if name not in _wifi_list:
            return
        logger.info("Connecting network {}".format(name))
        Process.exec_run(['sudo', 'nmcli', 'connection', 'up', name], sudo=True)

    def nmcli_wifi_list(device, *args, **kwargs):
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

    def nmcli_toggle_ap(device, *args, **kwargs):
        _profiles = Capability.nmcli_profile_list(device, *args, **kwargs)
        if not Capability.nmcli_ap_active(_profiles):
            logger.info("Activating Access Point.")
            if 'framarama' not in _profiles:
                Process.exec_run(['sudo', '-n', 'nmcli', 'device', 'wifi', 'hotspot', 'con-name', 'framarama', 'ssid', 'framaRAMA', 'password', 'framarama', 'band', 'bg'], sudo=True)
            else:
                Process.exec_run(['sudo', '-n', 'nmcli', 'connection', 'up', 'framarama'], sudo=True)
        else:
            logger.info("Deactivating Access Point.")
            Process.exec_run(['sudo', '-n', 'nmcli', 'connection', 'delete', 'framarama'], sudo=True)

    def app_log_systemd(device, *args, **kwargs):
        return Process.exec_run(['sudo', '-n', 'systemctl', 'status', '-n', '100', 'framarama'], sudo=True)

    def app_restart_systemd(device, *args, **kwargs):
        return Process.exec_run(['sudo', '-n', 'systemctl', 'restart', 'framarama'], sudo=True)

    def app_shutdown(device, *args, **kwargs):
        return Process.exec_run(['sudo', 'shutdown', '-h', 'now'], sudo=True)

    def _git_remotes():
        _remotes = Process.exec_run(['git', 'remote', '-v'])
        _remotes = [_line.split() for _line in _remotes.decode().split('\n') if len(_line)] if _remotes else []
        _remotes = {_parts[0]: _parts[1] for _parts in _remotes if _parts[-1] == '(fetch)'}
        return _remotes

    def _git_revisions():
        _revisions = []
        _out = Process.exec_run(['git', 'branch', '-r'])
        if _out:
            _out = [_line.strip() for _line in _out.decode().split('\n')]
            _revisions.extend(_out)
        _out = Process.exec_run(['git', 'tag', '-l'])
        if _out:
            _out = [_line for _line in _out.decode().split('\n')]
            _revisions.extend(_out)
        return [_rev for _rev in _revisions if len(_rev)]

    def _git_current_ref(refs):
        _refs = [_ref.strip() for _ref in refs.split(',')]        # separate tags
        _refs = [_ref.replace('HEAD -> ', '') for _ref in _refs]  # remove HEAD pointer
        _refs = [_ref.replace('tag: ', '') for _ref in _refs]     # remove tag: prefix
        if 'HEAD' in _refs:
            _refs.remove('HEAD')
        return _refs[0] if len(_refs) else None

    def app_revision(device, *args, **kwargs):
        _log = Process.exec_run(['git', 'log', '-1', '--pretty=format:%h %aI %d %s', '--decorate'])
        # de4a83b 2022-12-17T11:14:06+01:00  (HEAD, tag: v0.2.0) Implement frontend capability to retrieve display size (using xrandr)
        # 7034857 2023-01-07T11:42:25+01:00  (HEAD -> master) Silent sudo check command execution in Process.exec_run()
        if _log:
            _commit, _date, _values = _log.decode().split(maxsplit=2)
            _refs, _comment = _values[1:].split(') ', maxsplit=1)
            _branch = Process.exec_run(['git', 'branch', '--show-current'])
            _branch = _branch.decode().strip() if _branch else None
            _rev = {
                'hash': _commit,
                'date': DateTime.parse(_date),
                'comment': _comment,
                'branch': _branch,
                'remotes': Capability._git_remotes(),
                'revisions': Capability._git_revisions(),
                'current': Capability._git_current_ref(_refs),
            }
            return _rev
        return None

    def app_check(device, remote, url, username, password, *args, **kwargs):
        _url = re.sub(r'^(.*://)([^@]+@)?(.*)', '\\1' + re.escape(username) + '@\\3', url)
        logger.info("Check version update from {} using {} ...".format(remote, _url))
        _remotes = Capability._git_remotes()
        if remote in _remotes:
            logger.info("Update remote {} to {}".format(remote, _url))
            _remote_update = Process.exec_run(['git', 'remote', 'set-url', remote, _url])
        else:
            logger.info("Adding remote {} to {}".format(name, _url))
            _remote_update = Process.exec_run(['git', 'remote', 'add', name, _url])
        if _remote_update is None:
            logger.error("Can not setup remote {} with {}".format(name, _url))
            return
        _fetch = Process.exec_run(['git', 'fetch', remote], env={
            'GIT_ASKPASS': settings.BASE_DIR / 'docs' / 'git' / 'git-ask-pass.sh' ,
            'GIT_PASSWORD': password,
        })
        if _fetch is None:
            logger.error("Can not fetch updates!")
        else:
            logger.info("Updates fetched!")
        Process.exec_run(['git', 'remote', 'set-url', remote, url])

    def app_update(device, revision, *args, **kwargs):
        logger.info("Check version update ...")
        _revisions = Capability._git_revisions()
        if revision not in _revisions:
            logger.error("Can not update to non-existant revision {}".format(revision))
            return
        _stash = Process.exec_run(['git', 'stash'])
        if _stash is None:
            logger.error("Can not stash changes!")
            return
        logger.info("Changes stashed!")
        _pull = Process.exec_run(['git', 'checkout', revision])
        if _pull is None:
            logger.error("Can checkout revision!")
        else:
            logger.info("Revision checked out!")
        _pop = Process.exec_run(['git', 'stash', 'pop'])
        if _pop is None:
            logger.error("Can pop stash again!")



