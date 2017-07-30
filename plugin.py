from collections import namedtuple
import re
import networkx as nx
import networkx.drawing.nx_pydot as nx_pydot
from subprocess import call

StatusParsed = namedtuple('StatusParsed', ['target', 'proxy_level'])
NodeInfo = namedtuple('NodeInfo', [
                      'node', 'program', 'node_type', 'disabled_for', 'node_effect', 'childs'])
ProgramInfoParsed = namedtuple('StatusParsed', [
                               'program', 'effect', 'inevitable_effect', 'node_types', 'duration'])
AttackParsed = namedtuple(
    'StatusParsed', ['attack_program', 'defense_program', 'success'])
DontCareParsed = namedtuple('DontCareParsed', [])


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
        effect = None
        mm = re.search('Node effect: (.*)\n', msg, re.MULTILINE)
        if mm:
            effect = mm.group(1)

        disabled_for = None
        mm = re.search('DISABLED for: (\d*) sec\n', msg, re.MULTILINE)
        if mm:
            disabled_for = int(mm.group(1))

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
                child_nodes.append(NodeInfo(node=mmm.group(1),
                                            node_type=mmm.group(2), program=child_program,
                                            disabled_for=None, node_effect=None, childs=None))

        return NodeInfo(node, program, node_type, disabled_for, effect, child_nodes)

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

    def UpdateNodeLabel(self, name, node):
        if 'program' not in node.keys():
            program_str = '???'
        else:
            program_str = str(node['program'])
        label = name + '\n' + str(program_str)
        node['label'] = label

    def OnNodeInfo(self, node_info):
        self.AddOrUpdateNode(node_info)
        for child in node_info.childs:
            self.AddOrUpdateNode(child)
            self.graph.add_edge(node_info.node, child.node)
        if not node_info.childs and node_info.disabled_for:
            self.graph.add_edge(node_info.node, node_info.node)

    def AddOrUpdateNode(self, node_info):
        if not self.graph.has_node(node_info.node):
            self.graph.add_node(node_info.node)
        if node_info.program:
            self.graph.node[node_info.node]['program'] = node_info.program
        self.UpdateNodeLabel(node_info.node, self.graph.node[node_info.node])

    def OnAttackParsed(self, attack_parsed, target):
        self.graph.node[target]['program'] = attack_parsed.defense_program
        self.UpdateNodeLabel(target, self.graph.node[target])

    def PrintToPdf(self, name):
        dot_file_name = 'output/%s.dot' % name
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


def prof_pre_chat_message_display(barejid, resource, message):
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
        return

    if not parsed:
        print('<---')
        print(message)
        print('--->')


def prof_pre_chat_message_send(barejid, message):
    global last_command
    last_command = message
    return None


def PrintDot():
    global processors
    for name, processor in processors.items():
        processor.PrintToPdf(name)
