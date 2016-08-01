#!/usr/bin/env python
# encoding: utf-8

"""
@Create on: 2016-06-29 12:59
@Author: Rosen
"""
from __future__ import print_function

import argparse
import sys
from pyzabbix.api import ZabbixAPI


class Zabbix_Api:
    def __init__(self, idc='qc'):
        qc_url = ''
        xg_url = ''
        qc_auth = ''
        xg_auth = ''
        self.url = qc_url if idc == 'qc' else xg_url
        self.auth = qc_auth if idc == 'qc' else xg_auth

        self.z = ZabbixAPI(url=self.url, use_auth=True, auth=self.auth)

    def Get_Token(self, user=None, password=None):
        try:
            token = self.z._login(user=user, password=password)
            return token
        except Exception as e:
            print(e)

    # 获取id,支持扩展获取所有id
    def Get_ID(self,
               HostName=None,
               Template=None,
               ScreenName=None,
               Action='filter',
               Macros_Flag=False,
               Filter_Flag=False):
        if HostName and len(HostName) <= 6:
            exit('Warning: Hostname so short')
        if HostName and '*' in HostName:
            HostName = ''.join(HostName.split('*'))
            Filter_Flag = True

        Get_Input = HostName or Template or ScreenName
        Host_List = []
        Host_ID = []
        Template_List = []
        Template_ID = []
        Screen_ID = []
        Screen_List = []
        try:
            for l in Get_Input.split(','):
                if HostName:
                    Host_List.append(l)
                elif Template:
                    Template_List.append(l)
                elif ScreenName:
                    Screen_List.append(l)
            if Host_List:
                # 模糊匹配与精确查询
                Action = 'search' if Filter_Flag else Action
                # Group_Flag = True if GroupName else Group_Flag
                for h in Host_List:
                    host_id = self.z.do_request('host.get',
                                                params={'output': ['host', 'hostid'], "%s" % Action: {'host': h}})
                    res = sorted(host_id['result'], key=lambda x: int(x['host'].split('-')[-1]))
                    for i in res:
                        del i['host']
                        Host_ID.append(i)
                return Host_ID

            elif Template_List:
                for t in Template_List:
                    if Macros_Flag:
                        re = self.z.do_request('template.get',
                                               params={'selectMacros': ['macro', 'value'], 'filter': {'host': t}})
                        macros = re['result'][0]['macros']
                        for i in macros:
                            i.pop('hosts')
                        data = re['result']
                        Template_ID.extend(data)
                    re = self.z.do_request('template.get', params={'output': 'templateid', 'filter': {'host': t}})
                    data = re['result']
                    Template_ID.extend(data)
                return Template_ID
            elif Screen_List:
                for s in Screen_List:
                    re = self.z.do_request('screen.get', params={'output': 'screenid', 'filter': {'name': s}})
                    Screen_ID.append(re['result'][0]['screenid'])
                return Screen_ID

        except Exception as e:
            print(e)

    def Get_GroupID(self, GroupName=None):
        try:
            Group_ID = self.z.do_request('hostgroup.get', params={'output': 'extend', 'filter': {'name': GroupName}})
            return Group_ID['result'][0]['groupid']
        except Exception as e:
            print(e)

    def Get_GraphID(self, HostName=None, GraphName=None, Columns=3):
        Graph_ID = []
        Graph_List = []
        x = 0
        y = 0
        try:
            Host_ID = self.Get_ID(HostName=HostName)
            Only_Host_ID = map(lambda x: x.values()[0], Host_ID)
            for hostid in Only_Host_ID:
                re_graphid = self.z.do_request('graph.get',
                                               params={'output': ['graphid'],
                                                       'hostids': hostid,
                                                       'softfield': 'graphid', 'search': {'name': GraphName}})
                if re_graphid['result']:
                    Graph_ID.append(re_graphid['result'][0]['graphid'])
                else:
                    exit('Some host not have the graph: "%s" !' % GraphName)
            for graph in Graph_ID:
                Graph_List.append({
                    'resourcetype': '0',
                    'resourceid': graph,
                    'width': '500',
                    'height': '200',
                    'x': str(x),
                    'y': str(y),
                    'colspan': '0',
                    'rowspan': '0',
                    'elements': '0',
                    'valign': '0',
                    'halign': '0',
                    'style': '0',
                    'url': '',
                    'dynamic': '0'
                })
                x += 1
                if x == int(Columns):
                    x = 0
                    y += 1
            return Graph_ID, Graph_List
        except Exception as e:
            print(e)

    def Screen_Create(self, HostName=None, GraphName=None, ScreenName=None, Columns=3):
        try:
            Graph_ID, Graph_List = self.Get_GraphID(HostName=HostName, GraphName=GraphName)
            if len(Graph_ID) % Columns == 0:
                vsize = len(Graph_ID) / Columns
            else:
                vsize = (len(Graph_ID) / Columns) + 1

            Screen_ID = self.Get_ID(ScreenName=ScreenName)[0]
            if Screen_ID:
                re = self.z.do_request('screen.update', params={'screenid': Screen_ID,
                                                                'name': ScreenName,
                                                                'screenitems': Graph_List,
                                                                'hsize': Columns,
                                                                'vsize': vsize})
                if re['result']['screenids']:
                    print('The screen : "%s" has been update!' % ScreenName)
            else:
                re = self.z.do_request('screen.create',
                                       params={'name': ScreenName, 'hsize': Columns, 'vsize': vsize,
                                               'screenitems': Graph_List})
                if re['result']['screenids']:
                    print('The screen name: "%s" create succeed!' % ScreenName)
                    sys.exit(0)
                exit('Screen create failed')
        except Exception as e:
            print(e)

    def Create_Template(self, TemplateName=None, LinkTemplate=None, Template_ID=None, Macros=None):
        try:
            if LinkTemplate:
                Template_Info = self.Get_ID(Template=LinkTemplate, Macros_Flag=True)[0]
                Template_ID = Template_Info['templateid']
                Macros = Template_Info['macros']
            re = self.z.do_request('template.create',
                                   params={'host': TemplateName, 'groups': {'groupid': 1},
                                           'templates': Template_ID,
                                           'macros': Macros})
            if re['result']['templateids']:
                print('Template "%s" create succeed!' % TemplateName)
        except Exception as e:
            print(e)

    def Delete_Template(self, TemplateName=None):
        Template_List = []
        try:
            Template_ID = self.Get_ID(Template=TemplateName)[0]['templateid']
            Template_List.append(Template_ID)
            re = self.z.do_request('template.delete', params=Template_List)
            if re['result']['templateids']:
                print('Template "%s" has been delete!' % TemplateName)
        except Exception as e:
            print(e)

    def Mass_Remove_Templates(self, HostName=None, Templates=None):
        data = []
        try:
            Host_ID = self.Get_ID(HostName=HostName)
            Only_Host_ID = map(lambda x: x.values()[0], Host_ID)
            for t in Templates.split(','):
                Template_ID = self.Get_ID(Template=t)[0]['templateid']
                re = self.z.do_request('host.massremove',
                                       params={'hostids': Only_Host_ID, 'templateids_clear': Template_ID})
                data.append(re['result'])
            if data:
                print('template has been unlink!')
                sys.exit(0)
            exit('template unlink failure!')
        except Exception as e:
            print(e)

    def Mass_Add_Templates(self, HostName=None, Templates=None):
        Templates_List = []
        data = []
        try:
            Host_ID = self.Get_ID(HostName=HostName)
            for t in Templates.split(','):
                Templates_ID = self.Get_ID(Template=t)
                Templates_List.extend(Templates_ID)
                re = self.z.do_request('host.massadd', params={'hosts': Host_ID, 'templates': Templates_List})
                data.append(re['result'])
            if data:
                print('Template has been link!')
                sys.exit(0)
            exit('Template link failure!')
        except Exception as e:
            print(e)

    def Mass_Groups(self, HostName=None, GroupName=None, Method=None):
        Group_ID = self.Get_GroupID(GroupName=GroupName)
        Hosts_ID = self.Get_ID(HostName=HostName)
        Only_Host_ID = map(lambda x: x.values()[0], Hosts_ID)
        Mass = 'host.mass'
        try:
            if Method == 'replace':
                Method = Mass + 'update'
            elif Method == 'add':
                Method = Mass + 'add'
            re = self.z.do_request(Method, params={'hosts': Hosts_ID, 'groups': [{'groupid': Group_ID}]})
            if re['result']['hostids']:
                print('hosts information has been updated!')
            elif Method == 'remove':
                re = self.z.do_request('host.massremove', params={'hostids': Only_Host_ID, 'groupids': Group_ID})
                if re['result']['hostids']:
                    print('hosts information has been updated!')

        except Exception as e:
            print(e)

    def Method(self, ScreenName=None):
        try:
            Screen_ID = self.Get_ID(ScreenName=ScreenName)
            re = self.z.do_request('screen.delete', params=Screen_ID)['result']['screenids']
            if re:
                print('%s has been delete' % ScreenName)
                sys.exit(0)
            print('The given screen name: "%s" not exists' % ScreenName)
        except Exception as e:
            print(e)

    def Disable_Host(self, HostName=None, Method=None):
        status = 0
        data = []
        try:
            status = 1 if Method == 'disable' else status
            Hostids = self.Get_ID(HostName=HostName)
            if not Hostids:
                exit('"%s" not exists!' % HostName)
            for h in Hostids:
                re = self.z.do_request('host.massupdate', params={'hosts': h, 'status': status})
                data.append(re['result']['hostids'])
            if not data:
                exit('"%s" failed!' % Method)
            print('hosts has been "%s" !' % Method)
        except Exception as e:
            print(e)

    def main(self):
        if len(sys.argv) == 1:
            parse.print_help()
        else:
            args = parse.parse_args()
            Method = ['delete', 'disable', 'enable', 'replace', 'remove', 'add', 'create']
            # print(args)
            if args.idc == 'xg':
                self.__init__(idc='xg')
            if args.method_link == 'unlink' and args.template and args.hostname:
                self.Mass_Remove_Templates(HostName=args.hostname, Templates=args.template)
            elif args.method_link == 'link' and args.template and args.hostname:
                self.Mass_Add_Templates(HostName=args.hostname, Templates=args.template)
            elif args.screen and args.hostname and args.graph:
                self.Screen_Create(HostName=args.hostname, GraphName=args.graph, ScreenName=args.screen)
            elif args.graph and args.hostname:
                self.Get_GraphID(HostName=args.hostname, GraphName=args.graph)
            elif args.method:
                if args.screen and args.method in Method:
                    self.Method(ScreenName=args.screen)
                elif args.group and args.hostname and args.method in Method:
                    self.Mass_Groups(HostName=args.hostname, GroupName=args.group, Method=args.method)
                elif args.method == 'create' and args.template or args.link_template:
                    self.Create_Template(TemplateName=args.template, LinkTemplate=args.link_template)
                elif args.method == 'delete' and args.template:
                    self.Delete_Template(TemplateName=args.template)
                elif args.hostname and args.method in Method:
                    self.Disable_Host(HostName=args.hostname, Method=args.method)
            elif args.hostname or args.template:
                re = self.Get_ID(HostName=args.hostname, Template=args.template)
                print(re)


if __name__ == '__main__':
    parse = argparse.ArgumentParser(description='Zabbix API', usage='%(prog)s [options]')
    parse.add_argument('-I,', '--idc', dest='idc', type=str, help='Specify IDC name; Example: -I "xg" or -I "qc"')
    parse.add_argument('-H,', dest='hostname', type=str,
                       help='Support that match the given wildcard search..'
                            ' Example: -H "qc-moses-async*"',
                       metavar='hostname')
    parse.add_argument('-T,', dest='template', help='zabbix template; Example: -T "Template OS Linux"',
                       metavar='template')

    parse.add_argument('-L,', dest='method_link', help='Unlink a templates and clear form the given hosts. '
                                                       'Link a template from the hosts. '
                                                       'Example: -L "link" or -L "unlink"', metavar='link or unlink')
    parse.add_argument('-G,', dest='graph', help='get graph name from the given name', metavar='graph')
    parse.add_argument('-S,', dest='screen', help='create screen from the given hosts', metavar='screen')
    parse.add_argument('-M,', dest='method',
                       help='support "delete screen", "disable, enable hosts", "replace, remove, add group",'
                            ' "create template", "delete template" .'
                            ' Example: -M "delete" -S "test screen"',
                       metavar='method')
    parse.add_argument('-g,', dest='group', help='groups information', metavar='group')
    parse.add_argument('-l,', dest='link_template', help='Templates to be linked to the template',
                       metavar='link template')
    zabbix = Zabbix_Api()

    zabbix.main()
