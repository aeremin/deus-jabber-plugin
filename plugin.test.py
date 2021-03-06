import unittest
import unittest.mock as mock
import sys
sys.modules['prof'] = mock.MagicMock()
import plugin


class MyTest(unittest.TestCase):
    def testParsesStatusNoTarget(self):
        msg = '''
--------------------
willy220 status:
Current target: not set
Current administrating system: none
Proxy level: 6
Current proxy address: kenguru3362@sydney
END ----------------
        '''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.StatusParsed)
        self.assertIsNone(parsed.target)
        self.assertEqual(parsed.proxy_level, 6)

    def testParsesStatusWithTarget(self):
        msg = '''
--------------------
willy220 status:
Current target: ManInBlack
Current administrating system: none
Proxy level: 2
Current proxy address: coder5133@mumbai
END ----------------
        '''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.StatusParsed)
        self.assertEqual(parsed.target, 'ManInBlack')
        self.assertEqual(parsed.proxy_level, 2)

    def testParsesLook(self):
        msg = '''
--------------------
Node "ManInBlack/firewall" properties:
Installed program: #2209900
Type: Firewall
DISABLED for: 440 sec
Child nodes:
0: antivirus1 (Antivirus): #1811628
1: antivirus2 (Antivirus): #16530052 DISABLED

END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.NodeInfo)
        self.assertEqual(parsed.node, 'firewall')
        self.assertEqual(parsed.program, 2209900)
        self.assertEqual(parsed.node_type, 'Firewall')
        self.assertTrue(parsed.disabled)
        self.assertEqual(parsed.node_effect, 'NoOp')
        self.assertEqual(parsed.childs, [
                         plugin.MakeChildNodeInfo('antivirus1',
                                         1811628, 'Antivirus', False),
                         plugin.MakeChildNodeInfo('antivirus2',
                                         16530052, 'Antivirus', True)])

    def testParsesLookWithNodeEffect(self):
        msg='''
--------------------
Node "ManInBlack/VPN1" properties:
Installed program: #6162975
Type: VPN
Node effect: trace
END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.NodeInfo)
        self.assertEqual(parsed.node, 'VPN1')
        self.assertEqual(parsed.program, 6162975)
        self.assertEqual(parsed.node_type, 'VPN')
        self.assertFalse(parsed.disabled)
        self.assertEqual(parsed.node_effect, 'trace')
        self.assertEqual(parsed.childs, [])

    def testParsesLookWithEncryptedNode(self):
        msg = '''
--------------------
Node "LadyInRed5000/cryptocore1" properties:
Installed program: *encrypted*
Type: Cyptographic system
Locked for: 1658 sec
DISABLED for: 644 sec
Child nodes:
0: traffic_monitor1 (Traffic monitor): #3184236 DISABLED locked
1: VPN4 (VPN): #5887791 DISABLED locked

END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.NodeInfo)
        self.assertEqual(parsed.node, 'cryptocore1')
        self.assertIsNone(parsed.program)
        self.assertEqual(parsed.node_type, 'Cyptographic system')
        self.assertTrue(parsed.disabled)
        self.assertEqual(parsed.node_effect, 'NoOp')
        self.assertEqual(parsed.childs, [
                         plugin.MakeChildNodeInfo('traffic_monitor1',
                                         3184236, 'Traffic monitor', True),
                         plugin.MakeChildNodeInfo('VPN4', 5887791, 'VPN', True)])

    def testParsesLookWithEncryptedChild(self):
        msg = '''
--------------------
Node "BlackMirror944/brandmauer3" properties:
Installed program: #2294523
Type: Brandmauer
DISABLED for: 591 sec
Child nodes:
0: cryptocore3 (Cyptographic system): *encrypted*
1: VPN4 (VPN): #2209900

END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.NodeInfo)
        self.assertEqual(parsed.node, 'brandmauer3')
        self.assertEqual(parsed.program, 2294523)
        self.assertEqual(parsed.node_type, 'Brandmauer')
        self.assertTrue(parsed.disabled)
        self.assertEqual(parsed.node_effect, 'NoOp')
        self.assertEqual(parsed.childs, [
                         plugin.MakeChildNodeInfo('cryptocore3',
                                         None, 'Cyptographic system', False),
                         plugin.MakeChildNodeInfo('VPN4', 2209900, 'VPN', False)])

    def testParsesDefenseProgramInfo(self):
        msg = '''
--------------------
#2209900 programm info:
Effect: trace
Inevitable effect: logname
Allowed node types:
 -Firewall
 -Antivirus
 -VPN
 -Brandmauer
 -Router
 -Traffic monitor
 -Cyptographic system
END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.ProgramInfoParsed)
        self.assertEqual(parsed.program, 2209900)
        self.assertEqual(parsed.effect, 'trace')
        self.assertEqual(parsed.inevitable_effect, 'logname')
        self.assertEqual(parsed.node_types, ['Firewall', 'Antivirus', 'VPN',
                                             'Brandmauer', 'Router', 'Traffic monitor', 'Cyptographic system'])
        self.assertIsNone(parsed.duration)

    def testParsesAttackProgramInfo(self):
        msg = '''
--------------------
#1100 programm info:
Effect: disable
Allowed node types:
 -Firewall
 -Antivirus
 -VPN
 -Brandmauer
 -Router
 -Traffic monitor
 -Cyptographic system
Duration: 600sec.
END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.ProgramInfoParsed)
        self.assertEqual(parsed.program, 1100)
        self.assertEqual(parsed.effect, 'disable')
        self.assertEqual(parsed.node_types, ['Firewall', 'Antivirus', 'VPN',
                                             'Brandmauer', 'Router', 'Traffic monitor', 'Cyptographic system'])
        self.assertEqual(parsed.duration, 600)

    def testParsesGetDataProgramInfo(self):
        msg = '''
--------------------
#450 programm info:
Effect: get_data
Allowed node types:
 -Data
 -Bank account
 -Finance
 -Administrative interface
 -Corporate HQ
Duration: 600sec.
END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.ProgramInfoParsed)
        self.assertEqual(parsed.program, 450)
        self.assertEqual(parsed.effect, 'get_data')
        self.assertEqual(parsed.node_types, ['Data', 'Bank account', 'Finance',
                                             'Administrative interface', 'Corporate HQ'])
        self.assertEqual(parsed.duration, 600)

    def testParsesFailedAttack(self):
        msg = '''
executing program #2548 from willy220 target:LadyInRed351
Node defence: #2616796
attack failed
Trace:
Proxy level decreased by 1.
LadyInRed351 security log updated
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.AttackParsed)
        self.assertEqual(parsed.attack_program, 2548)
        self.assertEqual(parsed.defense_program, 2616796)
        self.assertFalse(parsed.success)

    def testParsesSuccessfulAttack(self):
        msg = '''
executing program #2028 from willy220 target:LadyInRed351
Node defence: #249444
attack successfull
Node 'antivirus1' disabled for 600 seconds.
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.AttackParsed)
        self.assertEqual(parsed.attack_program, 2028)
        self.assertEqual(parsed.defense_program, 249444)
        self.assertTrue(parsed.success)

    def testParsesSuccessfulAttackInevitableEffect(self):
        msg = '''
executing program #175 from willy220 target:ManInBlack
Node defence: #1189475
Inevitable effect triggered
Logname:
ManInBlack security log updated
attack successfull
Node 'antivirus4' disabled for 600 seconds.
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.AttackParsed)
        self.assertEqual(parsed.attack_program, 175)
        self.assertEqual(parsed.defense_program, 1189475)
        self.assertTrue(parsed.success)

    def testParsesSuccessfulAttackInevitableEffectOfNode(self):
        msg = '''
executing program #847 from willy220 target:LadyInRed351
Trace:
Proxy level decreased by 1.
LadyInRed351 security log updated
Node defence: #8247239
attack successfull
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.AttackParsed)
        self.assertEqual(parsed.attack_program, 847)
        self.assertEqual(parsed.defense_program, 8247239)
        self.assertTrue(parsed.success)

    def testDontCareAboutOk(self):
        msg = 'ok'
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.DontCareParsed)

    def testDontCareAboutNotAvailable(self):
        msg = '''
--------------------
BlackMirror944/antivirus not available

END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.DontCareParsed)

    def testIsCyberSpaceBot(self):
        self.assertTrue(plugin.IsCyberSpaceBot('raven@jabber.alice.digital'))
        self.assertTrue(plugin.IsCyberSpaceBot('darknet@cyberspace'))
        self.assertFalse(plugin.IsCyberSpaceBot('vasya@cyberspace'))

if __name__ == '__main__':
    unittest.main()
