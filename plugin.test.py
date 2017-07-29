import unittest
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
        self.assertIsInstance(parsed, plugin.LookParsed)
        self.assertEqual(parsed.node, 'ManInBlack/firewall')
        self.assertEqual(parsed.program, 2209900)
        self.assertEqual(parsed.node_type, 'Firewall')
        self.assertEqual(parsed.disabled_for, 440)
        self.assertIsNone(parsed.node_effect)
        self.assertEqual(parsed.childs, [
                         ('antivirus1', 'Antivirus', 1811628), ('antivirus2', 'Antivirus', 16530052)])

    def testParsesLookWithNodeEffect(self):
        msg = '''
--------------------
Node "ManInBlack/VPN1" properties:
Installed program: #6162975
Type: VPN
Node effect: trace
END ----------------
'''
        parsed = plugin.ParseIncomingMessage(msg)
        self.assertIsInstance(parsed, plugin.LookParsed)
        self.assertEqual(parsed.node, 'ManInBlack/VPN1')
        self.assertEqual(parsed.program, 6162975)
        self.assertEqual(parsed.node_type, 'VPN')
        self.assertIsNone(parsed.disabled_for)
        self.assertEqual(parsed.node_effect, 'trace')
        self.assertEqual(parsed.childs, [])

    def testParsesLookWithEncrypted(self):
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
        self.assertIsInstance(parsed, plugin.LookParsed)
        self.assertEqual(parsed.node, 'BlackMirror944/brandmauer3')
        self.assertEqual(parsed.program, 2294523)
        self.assertEqual(parsed.node_type, 'Brandmauer')
        self.assertEqual(parsed.disabled_for, 591)
        self.assertIsNone(parsed.node_effect)
        self.assertEqual(parsed.childs, [
                         ('cryptocore3', 'Cyptographic system', None), ('VPN4', 'VPN', 2209900)])

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



if __name__ == '__main__':
    unittest.main()
