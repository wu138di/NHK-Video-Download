import unittest
import os,time
from pathlib import Path
from tempfile import TemporaryDirectory
from subtitle_cleaner import clean_text,clean_srt,ass_to_srt,clean_ass,convert,read_text

SRT='9\n02:43:05,704 --> 02:43:07,673\n[CS][CS][SWF_7][SDF_840_480][SDP_58_29][SHS_4][SVS_24][SSM_36_36][MSZ][APS_7_15][NSZ][WHF][COL_4][COL_5_1]≪[MSZ]（[NSZ]風鈴の音[MSZ]）\n\n10\n02:43:07,673 --> 02:43:10,593\n[NSZ]お風呂上がりに[MSZ]　[NSZ]うちわの風…[MSZ]。\n'
ASS='[Script Info]\nScriptType: v4.00+\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 1,0:00:00.71,0:00:02.68,Default,,0,0,0,,{\\pos(360,497.75)\\fscx100}≪{\\fscx50}（{\\fscx100}風鈴の音{\\fscx50}）\nDialogue: 0,0:00:00.71,0:00:02.68,边框,,0,0,0,,{\\pos(358,497.4)\\bord12}≪（風鈴の音）\nDialogue: 1,0:00:00.71,0:00:02.68,Default,,0,0,0,,{\\pos(359,497.75)}≪（風鈴の音）\nDialogue: 1,0:00:02.68,0:00:05.60,Default,,0,0,0,,[NSZ]お風呂上がりに[MSZ]\\Nうちわの風…。\n'

class Tests(unittest.TestCase):
    def test_screenshot_srt(self):
        result,s=clean_srt(SRT)
        self.assertIn('≪（風鈴の音）',result)
        self.assertIn('お風呂上がりに　うちわの風…。',result)
        self.assertEqual(s['cues'],2)
        self.assertGreater(s['markers_removed'],15)
        for marker in ('[SDF','[SDP','[SSM','[APS','[COL'):
            self.assertNotIn(marker,result)
        self.assertEqual([l for l in SRT.splitlines() if '-->' in l],[l for l in result.splitlines() if '-->' in l])
    def test_preserve_bracket_dialogue(self):
        self.assertEqual(clean_text('[Music] [笑い] [A] [Custom_Tag]')[0],'[Music] [笑い] [A] [Custom_Tag]')
    def test_known_tags(self):
        self.assertEqual(clean_text('[SSZ][APS_14_17][COL_5_1]そういえば[MSZ]')[0],'そういえば')
    def test_ass_duplicate_layers(self):
        text,s=ass_to_srt(ASS)
        self.assertEqual(s['duplicate_layers_removed'],2)
        self.assertEqual(s['cues'],2)
        self.assertEqual(text.count('風鈴の音'),1)
        self.assertIn('00:00:00,710 --> 00:00:02,680',text)
        self.assertIn('お風呂上がりに\nうちわの風…。',text)
        self.assertNotIn('\\pos',text)
    def test_ass_preserve_layout(self):
        text,s=clean_ass(ASS)
        self.assertEqual(s['cues'],4)
        self.assertIn(r'\pos(360,497.75)',text)
        self.assertNotIn('[MSZ]',text)
    def test_drawings(self):
        t=ASS+'Dialogue: 1,0:00:06.00,0:00:07.00,Default,,0,0,0,,{\\p1}m 0 0 l 100 100\n'
        text,s=ass_to_srt(t)
        self.assertEqual(s['drawings_skipped'],1)
        self.assertNotIn('m 0 0',text)
    def test_same_interval_fragments(self):
        t=ASS+'Dialogue: 1,0:00:00.71,0:00:02.68,Default,,0,0,0,,別の声\n'
        text,s=ass_to_srt(t)
        self.assertIn('≪（風鈴の音）\n別の声',text)
    def test_malformed_srt(self):
        with self.assertRaises(ValueError):clean_srt('Not a subtitle')
    def test_invalid_ass_interval(self):
        with self.assertRaises(ValueError):ass_to_srt(ASS.replace('0:00:02.68','0:00:00.01'))
    def test_c0_controls(self):
        self.assertEqual(clean_text('前\x00\x0b\x7f後')[0],'前後')
    def test_source_preserved_and_overwrite_guard(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'日本語.srt'
            p.write_text(SRT,encoding='utf-8-sig')
            before=p.read_bytes()
            r=convert(p)
            self.assertEqual(p.read_bytes(),before)
            self.assertTrue(Path(r['output']).read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertIn(b'\r\n',Path(r['output']).read_bytes())
            with self.assertRaises(FileExistsError):convert(p)
            convert(p,force=True)
            with self.assertRaises(ValueError):convert(p,p,force=True)
    def test_cp932_and_utf16(self):
        with TemporaryDirectory() as d:
            for encoding in ('cp932','utf-16'):
                p=Path(d)/('字幕'+encoding+'.srt')
                p.write_text('風鈴の音',encoding=encoding)
                self.assertEqual(read_text(p),'風鈴の音')
    def test_empty_ass_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'empty.ass'
            p.write_text('[Events]\n',encoding='utf-8')
            with self.assertRaises(ValueError):convert(p)
    def test_ass_output_explicit(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'字幕.ass'
            p.write_text(ASS,encoding='utf-8')
            r=convert(p,output_format='ass')
            self.assertTrue(r['output'].endswith('.clean.ass'))
            self.assertIn(r'\pos',read_text(r['output']))
    def test_gui_completion_integration(self):
        from subtitle_integration import install
        with TemporaryDirectory() as d:
            folder=Path(d)
            class Main:
                def __init__(self):pass
                def _on_download_done(self,rc,save_sub,auto_convert):return 'original preserved'
            ns={'MainWindow':Main,'find_ffmpeg':lambda configured='':configured,
                'DEFAULT_CONFIG':{},'load_config':lambda:{'output_dir':d},'DEFAULT_OUTPUT_DIR':d}
            install(ns)
            app=object.__new__(Main)
            app.config={'output_dir':d}
            app._download_expected_name='current.mkv'
            app._download_started_at=time.time()-1
            app._append_log=lambda text:None
            for name in ('current.srt','other.srt','current-old.srt'):
                (folder/name).write_text(SRT,encoding='utf-8')
            os.utime(folder/'current-old.srt',(1,1))
            self.assertEqual(app._on_download_done(0,True,False),'original preserved')
            self.assertIn('≪（風鈴の音）',read_text(folder/'current.srt'))
            self.assertNotIn('[CS]',read_text(folder/'current.srt'))
            self.assertTrue(any((folder/'.subtitle-originals').glob('*.raw')))
            self.assertFalse((folder/'other.clean.srt').exists())
            self.assertFalse((folder/'current-old.clean.srt').exists())
            self.assertEqual(next((folder/'.subtitle-originals').glob('*.raw')).read_text('utf-8'),SRT)
    def test_gui_failure_does_not_clean(self):
        from subtitle_integration import install
        with TemporaryDirectory() as d:
            class Main:
                def __init__(self):pass
                def _on_download_done(self,rc,save_sub,auto_convert):return None
            ns={'MainWindow':Main,'find_ffmpeg':lambda configured='':configured,
                'DEFAULT_CONFIG':{},'load_config':lambda:{'output_dir':d},'DEFAULT_OUTPUT_DIR':d}
            install(ns)
            app=object.__new__(Main)
            app.config={'output_dir':d}
            app._download_expected_name='failed'
            app._download_started_at=time.time()-1
            (Path(d)/'failed.srt').write_text(SRT,encoding='utf-8')
            app._on_download_done(1,True,False)
            self.assertFalse((Path(d)/'failed.clean.srt').exists())

if __name__=='__main__':unittest.main(verbosity=2)
