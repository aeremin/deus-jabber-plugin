from collections import namedtuple
import re
import networkx as nx
import networkx.drawing.nx_pydot as nx_pydot
from subprocess import call

StatusParsed = namedtuple('StatusParsed', ['target', 'proxy_level'])
LookParsed = namedtuple('StatusParsed', [
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
                child_nodes.append((mmm.group(1), mmm.group(2), child_program))

        return LookParsed(node, program, node_type, disabled_for, effect, child_nodes)

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


Context = namedtuple('Context', ['current_system', 'proxy_level'])
last_command = ''
context = Context(None, None)
G = nx.DiGraph()
#G.graph['graph'] = {'rankdir': 'LR'}

def MakeNodePropertiesDict(name, program):
    if not program: program = '???'
    label = name + '\n' + str(program)
    return {'label': label}

def prof_pre_chat_message_display(barejid, resource, message):
    global last_command
    global G
    global context

    if message == 'ok':
        m = re.search('target ([a-zA-Z0-9_]*)', last_command, re.MULTILINE)
        context = Context(current_system=m.group(1), proxy_level=9000)

    parsed = ParseIncomingMessage(message)
    if isinstance(parsed, StatusParsed):
        context = Context(current_system=parsed.target,
                          proxy_level=parsed.proxy_level)

    if isinstance(parsed, LookParsed):
        if context.current_system != 'BlackMirror944':
            return
        G.add_node(parsed.node, MakeNodePropertiesDict(parsed.node, parsed.program))
        for child in parsed.childs:
            child_node = child[0]
            child_program = child[2]
            G.add_node(child_node, MakeNodePropertiesDict(child_node, child_program))
            G.add_edge(parsed.node, child_node)
        if not parsed.childs and parsed.disabled_for:
            G.add_edge(parsed.node, parsed.node)

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
    nx_pydot.write_dot(G, 'fe.dot')
    call(['dot', 'fe.dot', '-Tpdf:cairo', '-ofe.pdf'])