from collections import namedtuple
import re
import os
import networkx as nx
import networkx.drawing.nx_pydot as nx_pydot
from subprocess import call
import prof
import glob
import json


StatusParsed = namedtuple('StatusParsed', ['target', 'proxy_level'])
NodeInfo = namedtuple('NodeInfo', [
                      'node', 'program', 'node_type', 'disabled', 'node_effect', 'childs'])
ProgramInfoParsed = namedtuple('ProgramInfoParsed', [
                               'program', 'effect', 'inevitable_effect', 'node_types', 'duration'])
AttackParsed = namedtuple(
    'AttackParsed', ['attack_program', 'defense_program', 'success'])
DontCareParsed = namedtuple('DontCareParsed', [])

OUTPUT_LOCATION = '/home/aeremin/Dev/deus-jabber-plugin/output/'

def IsCyberSpaceBot(jid):
    return jid == 'darknet@cyberspace' or jid == 'raven@jabber.alice.digital'

def MakeChildNodeInfo(node, program, node_type, disabled):
    return NodeInfo(node, program, node_type, disabled, None, None)

# TODO: Change to actual rule
def TheRule(attack_program, defense_program):
    return (defense_program is not None and
        (defense_program % int(attack_program)) == 0)


def ParseIncomingMessage(msg):
    m = re.search('Current target: (.*)\n'
                  '.*\n'
                  'Proxy level: (\d+)',
                  msg, re.MULTILINE)
    if m:
        target = m.group(1)
        if target == 'not set':
            target = None
        return StatusParsed(target, int(m.group(2)))

    m = re.search('Node ".*/(.*)" properties:\n'
                  'Installed program: (#(\d+)|\*encrypted\*)\n'
                  'Type: (.*)\n',
                  msg, re.MULTILINE)
    if m:
        node = m.group(1)
        program = None
        if m.group(3):
            program = int(m.group(3))
        node_type = m.group(4)
        effect = 'NoOp'
        mm = re.search('Node effect: (.*)\n', msg, re.MULTILINE)
        if mm:
            effect = mm.group(1)

        disabled = re.search('DISABLED', msg, re.MULTILINE) is not None

        child_nodes = []
        mm = re.search('Child nodes:\n(.*)\n\n', msg,
                       re.MULTILINE and re.DOTALL)
        if mm:
            for line in mm.group(1).splitlines():
                mmm = re.match(
                    '\d*: ([a-zA-Z0-9_]*) \(([a-zA-Z0-9 ]*)\): (#(\d*)|\*encrypted\*)', line)
                child_program = None
                if mmm.group(4):
                    child_program = int(mmm.group(4))
                disabled_child = 'DISABLED' in line
                child_nodes.append(MakeChildNodeInfo(mmm.group(1), child_program,
                                                     mmm.group(2), disabled_child))

        return NodeInfo(node, program, node_type, disabled, effect, child_nodes)

    m = re.search('#(\d*) progra(m|mm) info:\n'
                  'Effect: ([a-zA-Z0-9_]*)\n',
                  msg, re.MULTILINE)
    if m:
        program = int(m.group(1))
        effect = m.group(3)
        inevitable_effect = None
        mm = re.search(
            'Inevitable effect: ([a-zA-Z0-9_]*)\n', msg, re.MULTILINE)
        if mm:
            inevitable_effect = mm.group(1)
        node_types = []
        mm = re.search('Allowed node types:\n(.*)',
                       msg, re.MULTILINE and re.DOTALL)
        if mm:
            for line in mm.group(1).splitlines():
                mmm = re.match(' -(.*)', line)
                if mmm:
                    node_types.append(mmm.group(1))
        duration = None
        mm = re.search('Duration: (\d*)(sec| sec)', msg, re.MULTILINE)
        if mm:
            duration = int(mm.group(1))
        return ProgramInfoParsed(program, effect, inevitable_effect, node_types, duration)

    m = re.search('(E|e)xecuting progra(m|mm) #(\d*).*\n'
                  '(.*\n)*'
                  'Node defence: #(\d*)\n'
                  '(.*\n)*'
                  '(A|a)ttack (.*)\n',
                  msg, re.MULTILINE)
    if m:
        return AttackParsed(int(m.group(3)),  int(m.group(5)), m.group(8) == 'successfull')

    if (msg in ['ok', '403 Forbidden'] or
        re.search('Info about .* effect:', msg, re.MULTILINE) or
        re.search('not available(| )\n', msg, re.MULTILINE) or
        re.search('Error 406: node disabled', msg, re.MULTILINE) or
            re.search('network scan started: ', msg, re.MULTILINE)):
        return DontCareParsed()

    return None


class PerSystemProcessor:
    def __init__(self, graph=None):
        self.graph = graph or nx.DiGraph()
        for _, node in self.graph.node.items():
            node['disabled'] = node.get('disabled', '') == 'True'
            p = node.get('program', None)
            if p: node['program'] = int(p)
        
    def OnNodeInfo(self, node_info):
        self.AddOrUpdateNode(node_info)
        for child in node_info.childs:
            self.AddOrUpdateNode(child)
            self.graph.add_edge(node_info.node, child.node)

    def AddOrUpdateNode(self, node_info):
        if not self.graph.has_node(node_info.node):
            self.graph.add_node(node_info.node)
        node = self.graph.node[node_info.node]
        self.MaybeSaveNodeProgram(node_info.node, node_info.program)
        if node_info.childs == [] and node_info.disabled:
            node['leaf'] = True
        node['disabled'] = node_info.disabled
        if node_info.node_effect:
            node['effect'] = node_info.node_effect

    def OnAttackParsed(self, attack_parsed, target):
        self.MaybeSaveNodeProgram(target, attack_parsed.defense_program)

    def MaybeSaveNodeProgram(self, node_name, program):
        if not program:
            return
        node = self.graph.node[node_name]
        node['program'] = program

    def UpdateNodeLabel(self, name, node):
        if 'program' not in node.keys():
            program_str = '???'
        else:
            program_str = str(node['program'])
        label = name + '\n' + str(program_str)
        node['label'] = label

    def PrintToPdf(self, name):
        for node_name, node in self.graph.node.items():
            self.UpdateNodeLabel(node_name, node)
            styles = ''
            if node.get('leaf', False):
                styles += 'diagonals,'
            if node.get('disabled', False):
                styles += 'dotted,'
            effect = node.get('effect', 'NoOp')
            if not effect == 'NoOp':
                styles += 'bold,'
            if styles:
                styles = styles[:-1]
            node['style'] = '"' + styles + '"'

        dot_file_name = '%sdot/%s.dot' % (OUTPUT_LOCATION, name)
        pdf_file_name = '%s%s.pdf' % (OUTPUT_LOCATION, name)
        nx_pydot.write_dot(self.graph, dot_file_name)
        call(['dot', dot_file_name, '-Tpdf:cairo', '-o%s' % pdf_file_name])


last_command = ''
proxy_level = None
current_system = None
processors = dict()
known_programs = dict()

def GetCurrentProcessor():
    global processors
    global current_system
    if not current_system:
        return None
    if not current_system in processors.keys():
        processors[current_system] = PerSystemProcessor()
    return processors[current_system]

def MakeHackTooltip(defense_program, defense_type):
    global known_programs
    winning_attacks = []
    for k, p in known_programs.items():
        if (TheRule(k, defense_program) and 
            (defense_type in p.node_types)):
            winning_attacks.append('%d:%s' % (k, p.effect))
    return '(' + ', '.join(winning_attacks) + ')'

def prof_init(version, status, account_name, fulljid):
    global processors
    global known_programs
    saved_graphs = glob.glob(OUTPUT_LOCATION + 'dot/*.dot')
    processors = dict()
    for g in saved_graphs:
        system_name = os.path.basename(os.path.splitext(g)[0])
        processors[system_name] = PerSystemProcessor(nx.DiGraph(nx_pydot.read_dot(g)))
    known_programs = dict()
    if os.path.isfile(OUTPUT_LOCATION + 'programs.json'):
        with open(OUTPUT_LOCATION + 'programs.json') as f:
            tmp = json.load(f)
            for k, v in tmp.items():
                known_programs[int(k)] = ProgramInfoParsed(v[0], v[1], v[2], v[3], v[4])


def prof_pre_chat_message_display_no_print(barejid, resource, message):
    if not IsCyberSpaceBot(barejid): return message
    prof.log_info('prof_pre_chat_message_display')
    prof.log_info("barejid: %s\nmessage: %s" % (barejid, message))

    global last_command
    global proxy_level
    global current_system
    global processors
    global known_programs

    if message == 'ok':
        m = re.search('target ([a-zA-Z0-9_]*)', last_command, re.MULTILINE)
        current_system = m.group(1)

    parsed = ParseIncomingMessage(message)
    if isinstance(parsed, StatusParsed):
        current_system = parsed.target
        proxy_level = parsed.proxy_level

    if isinstance(parsed, NodeInfo):
        GetCurrentProcessor().OnNodeInfo(parsed)
        last_know_program = GetCurrentProcessor().graph.node[parsed.node].get('program', None)
        if not parsed.program and last_know_program:
            message = message + '\nLast known defense program: %d' % last_know_program
        message = (message + '\nFollowing attacks are available:\n' + 
            MakeHackTooltip(last_know_program, parsed.node_type))

    if isinstance(parsed, AttackParsed):
        m = re.search('#\d+ ([a-zA-Z0-9_]+)', last_command, re.MULTILINE)
        GetCurrentProcessor().OnAttackParsed(
            parsed, m.group(1))

    if isinstance(parsed, ProgramInfoParsed):
        known_programs[parsed.program] = parsed
        with open(OUTPUT_LOCATION + 'programs.json', 'w') as f:
            json.dump(known_programs, f, indent=2)

    if isinstance(parsed, DontCareParsed):
        return message

    if not parsed:
        prof.log_warning('Not able to parse message:')
        prof.log_warning(message)
        prof.log_warning('(EOM)')
        return message
    return message

def prof_pre_chat_message_display(barejid, resource, message):
    res = prof_pre_chat_message_display_no_print(barejid, resource, message)
    if current_system:
        GetCurrentProcessor().PrintToPdf(current_system)

def prof_pre_chat_message_send(barejid, message):
    if not IsCyberSpaceBot(barejid): return message
    prof.log_info('prof_pre_chat_message_send')
    prof.log_info("barejid: %s\nmessage: %s" % (barejid, message))
    global last_command
    last_command = message
    return message


def PrintAllPdfs():
    global processors
    for name, processor in processors.items():
        processor.PrintToPdf(name)
