import unittest
from live_guard import is_live_source,contains_live

class Tests(unittest.TestCase):
    def test_sim_hosts(self):
        for value in ('https://sim.example.test/a.m3u8','https://simul-stream.example.test/master.mpd','https://SIM123.example.test/a'):
            self.assertTrue(is_live_source(value))
    def test_sim_paths(self):
        for value in ('https://media.example.test/simul/a.m3u8','https://media.example.test/sim_01.mpd'):
            self.assertTrue(is_live_source(value))
    def test_replay_passes(self):
        self.assertFalse(is_live_source('https://vod.example.test/replay/episode.m3u8'))
        self.assertFalse(contains_live({'title':'simulated programme','url':'https://vod.example.test/a.mpd'}))
    def test_envelope(self):
        self.assertTrue(contains_live({'payload':{'manifest_url':'https://sim.example.test/a.m3u8'}}))
    def test_supplied_continuous_source(self):
        self.assertTrue(is_live_source('http://tsb-mega.i9.ee/stream/nhkg_avc_1080p'))
        self.assertTrue(is_live_source('http://tsb-mega.i9.ee/stream/nhkg_hevc_1080p'))
    def test_bad_input(self):
        self.assertFalse(is_live_source(None))
        self.assertFalse(is_live_source('https://[broken'))

if __name__=='__main__':unittest.main(verbosity=2)
