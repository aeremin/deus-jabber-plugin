from collections import namedtuple
import re
import networkx as nx
import networkx.drawing.nx_pydot as nx_pydot
from subprocess import call

StatusParsed = namedtuple('StatusParsed', ['target', 'proxy_level'])
NodeInfo = namedtuple('NodeInfo', [
                      'node', 'program', 'node_type', 'disabled', 'node_effect', 'childs'])
ProgramInfoParsed = namedtuple('StatusParsed', [
                               'program', 'effect', 'inevitable_effect', 'node_types', 'duration'])
AttackParsed = namedtuple(
    'StatusParsed', ['attack_program', 'defense_program', 'success'])
DontCareParsed = namedtuple('DontCareParsed', [])


def IsCyberSpaceBot(jid):
    return jid == 'darknet@cyberspace' or jid == 'raven@jabber.alice.digital'



def MakeChildNodeInfo(node, program, node_type, disabled):
    return NodeInfo(node, program, node_type, disabled, None, None)


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
    def __init__(self):
        self.graph = nx.DiGraph()

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

        dot_file_name = 'output/dot/%s.dot' % name
        pdf_file_name = 'output/%s.pdf' % name
        nx_pydot.write_dot(self.graph, dot_file_name)
        call(['dot', dot_file_name, '-Tpdf:cairo', '-o%s' % pdf_file_name])


last_command = ''
proxy_level = None
current_system = None
processors = dict()


def GetCurrentProcessor():
    global processors
    global current_system
    if not current_system:
        return None
    if not current_system in processors.keys():
        # TODO: Support loading from file
        processors[current_system] = PerSystemProcessor()
    return processors[current_system]


import prof


def prof_pre_chat_message_display(barejid, resource, message):
    if not IsCyberSpaceBot(barejid): return message
    prof.log_info('prof_pre_chat_message_display')
    prof.log_info("barejid: %s\nmessage: %s" % (barejid, message))

    global last_command
    global proxy_level
    global current_system
    global processors

    if message == 'ok':
        m = re.search('target ([a-zA-Z0-9_]*)', last_command, re.MULTILINE)
        current_system = m.group(1)

    parsed = ParseIncomingMessage(message)
    if isinstance(parsed, StatusParsed):
        current_system = parsed.target
        proxy_level = parsed.proxy_level

    if isinstance(parsed, NodeInfo):
        GetCurrentProcessor().OnNodeInfo(parsed)

    if isinstance(parsed, AttackParsed):
        m = re.search('#\d+ ([a-zA-Z0-9_]+)', last_command, re.MULTILINE)
        GetCurrentProcessor().OnAttackParsed(
            parsed, m.group(1))

    if isinstance(parsed, DontCareParsed):
        return message

    if not parsed:
        prof.log_warning('Not able to parse message:')
        prof.log_warning(message)
        prof.log_warning('(EOM)')

    return message


def prof_pre_chat_message_send(barejid, message):
    if not IsCyberSpaceBot(barejid): return message
    prof.log_info('prof_pre_chat_message_send')
    prof.log_info("barejid: %s\nmessage: %s" % (barejid, message))
    global last_command
    last_command = message
    return message


def PrintDot():
    global processors
    for name, processor in processors.items():
        processor.PrintToPdf(name)
