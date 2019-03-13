#Copyright (C) 2009 eloquence fans
#synthDrivers/eci.py
#todo: possibly add to this
import speech
punctuation = ",.?:;"
punctuation = [x for x in punctuation]
from ctypes import *
import ctypes.wintypes
from ctypes import wintypes
import synthDriverHandler, os, config, re, Queue, nvwave, threading, logging
from logHandler import log
from synthDriverHandler import SynthDriver,VoiceInfo,BooleanSynthSetting
from synthDriverHandler import SynthDriver,VoiceInfo,NumericSynthSetting
import _eloquence
import languageHandler
from collections import OrderedDict
minRate=40
maxRate=150
anticrash_res = {
 re.compile(r'\b(|\d+|\W+)?(|un|anti|re)c(ae|\xe6)sur', re.I): r'\1\2seizur',
 re.compile(r"\b(|\d+|\W+)h'(r|v)[e]", re.I): r"\1h ' \2 e",
 re.compile(r"\b(\w+[bdflmnrvzqh])hes([bcdfgjklmnprtw]\w+)\b", re.I): r"\1 hes\2",
 re.compile(r"(\d):(\d\d[snrt][tdh])", re.I): r"\1 \2",
 re.compile(r"([hH])'([bBdDfFjJkKpPsStTvVxX]+)'([rR][aAeEiIoOuU]?)", re.I): r"\1 \2 \3",
 re.compile(r"(re|un|non|anti)cosp", re.I): r"\1kosp",
 re.compile(r"(anti|non|re|un)caesure", re.I): r"\1ceasure",
 re.compile(r"(EUR[A-Z]+)(\d+)", re.I): r"\1 \2",
 re.compile(r"\b(|\d+|\W+)?tz[s]che", re.I): r"\1tz sche"
}

pause_re = re.compile(r'([a-zA-Z])([.(),:;!?])( |$)')
time_re = re.compile(r"(\d):(\d+):(\d+)")
english_fixes = {
re.compile(r'(\w+)\.([a-zA-Z]+)'): r'\1 dot \2',
re.compile(r'([a-zA-Z0-9_]+)@(\w+)'): r'\1 at \2',
}
french_fixes = {
re.compile(r'([a-zA-Z0-9_]+)@(\w+)'): r'\1 arobase \2',
}
spanish_fixes = {
#for emails
re.compile(r'([a-zA-Z0-9_]+)@(\w+)'): r'\1 arroba \2',
}
variants = {1:"Reed",
2:"Shelley",
3:"Bobby",
4:"Rocko",
5:"Glen",
6:"Sandy",
7:"Grandma",
8:"Grandpa"}

# For langChangeCommand
langsAnnotations={
"en":"`l1",
"en_US":"`l1.0",
"en_UK":"`l1.1",
"en_GB":"`l1.1",
"es":"`l2",
"es_ES":"`l2.0",
"es_ME":"`l2.1",
"fr":"`l3",
"fr_FR":"`l3.0",
"fr_CA":"`l3.1",
"de":"`l4",
"de_DE":"`l4",
"it":"`l5",
"it_IT":"`l5",
"zh":"`l6",
"zh_gb":"`l6.0",
"pt":"`l7",
"pt_BR":"`l7.0",
"pt_PT":"`l7.1",
"ja":"`l8",
"ja_ja":"`l8.0",
"ko":"`l10",
"ko_ko":"`l10.0",
"fi":"`l9",
"fi_FI":"`l9.0"
}

class SynthDriver(synthDriverHandler.SynthDriver):
 supportedSettings=(SynthDriver.VoiceSetting(), SynthDriver.VariantSetting(), SynthDriver.RateSetting(), SynthDriver.PitchSetting(),SynthDriver.InflectionSetting(),SynthDriver.VolumeSetting(), NumericSynthSetting("hsz", "Head Size"), NumericSynthSetting("rgh", "Roughness"), NumericSynthSetting("bth", "Breathiness"), BooleanSynthSetting("backquoteVoiceTags","Enable backquote voice &tags", True), BooleanSynthSetting("ABRDICT","Enable &abbreviation dictionary", False))
 description='ETI-Eloquence'
 name='eloquence'
 speakingLanguage=""
 @classmethod
 def check(cls):
  return _eloquence.eciCheck()
 def __init__(self):
  _eloquence.initialize()
  # This information doesn't really need to be displayed, and makes Eloquence unusable if the addon is not in the same drive as NVDA executable.
  # But display it only on debug mode in case of it can be useful
  log.debug("Using Eloquence version %s" % _eloquence.eciVersion())
  lang = languageHandler.getLanguage()
  self.curvoice=_eloquence.getVoiceByLanguage(lang)
  self.rate=50
  self.speakingLanguage=lang
  self.variant="1"

 def speak(self,speechSequence):
#  print speechSequence
  last = None
  defaultLanguage=self.language
  outlist = []
  for item in speechSequence:
   if isinstance(item,basestring):
    s=unicode(item)
    s = self.xspeakText(s)
    outlist.append((_eloquence.speak, (s,)))
    last = s
   elif isinstance(item,speech.IndexCommand):
    outlist.append((_eloquence.index, (item.index,)))
   elif isinstance(item,speech.LangChangeCommand):
    if (item.lang and langsAnnotations.has_key(item.lang)):
     if self.speakingLanguage!=item.lang and item.lang!=self.speakingLanguage[0:2]:
      outlist.append((_eloquence.speak, (langsAnnotations[item.lang],)))
      self.speakingLanguage=item.lang
    elif (item.lang and langsAnnotations.has_key(item.lang[0:2])):
     if self.speakingLanguage!=item.lang and item.lang!=self.speakingLanguage[0:2]:
      outlist.append((_eloquence.speak, (langsAnnotations[item.lang[0:2]],)))
     self.speakingLanguage=item.lang[0:2]
    else:
     outlist.append((_eloquence.speak, (langsAnnotations[defaultLanguage],)))
     self.speakingLanguage = defaultLanguage
   elif isinstance(item,speech.CharacterModeCommand):
    outlist.append((_eloquence.speak, ("`ts1" if item.state else "`ts0",)))
   elif isinstance(item,speech.SpeechCommand):
    log.debugWarning("Unsupported speech command: %s"%item)
   else:
    log.error("Unknown speech: %s"%item)
  if last is not None and not last.rstrip()[-1] in punctuation:
   outlist.append((_eloquence.speak, ('`p1.',)))
  outlist.append((_eloquence.index, (0xffff,)))
  outlist.append((_eloquence.speak, ("`ts0",)))
  outlist.append((_eloquence.synth,()))
  _eloquence.synth_queue.put(outlist)
  _eloquence.process()

 def xspeakText(self,text, should_pause=False):
  if _eloquence.params[9] == 65536 or _eloquence.params[9] == 65537: text = resub(english_fixes, text)
  if _eloquence.params[9] == 131072 or _eloquence.params[9] == 131073: text = resub(spanish_fixes, text)
  if _eloquence.params[9] in (196609, 196608): text = resub(french_fixes, text)
  if self._backquoteVoiceTags:
   text = "`pp0 `vv%d %s" % (self.getVParam(_eloquence.vlm), text) #allow embedded commands
   if self._ABRDICT:
    text="`da1 "+text
   else:
    text="`da0 "+text
   #this converts to ansi for anticrash. If this breaks with foreign langs, we can remove it.
   text = text.encode('mbcs')
   text = resub(anticrash_res, text)
  else:
   #this converts to ansi for anticrash. If this breaks with foreign langs, we can remove it.
   text = text.encode('mbcs')
   text = resub(anticrash_res, text)
   text = "`pp0 `vv%d %s" % (self.getVParam(_eloquence.vlm), text.replace('`', ' ')) #no embedded commands
   if self._ABRDICT:
    text="`da1 "+text
   else:
    text="`da0 "+text
   if _eloquence.params[9] in (196609, 196608): text = text.replace('quil', 'qil') #Sometimes this string make everything buggy with Eloquence in French
  text = pause_re.sub(r'\1 `p0\2\3', text)
  text = time_re.sub(r'\1:\2 \3', text)
#if two strings are sent separately, pause between them. This might fix some of the audio issues we're having.
  if should_pause:
   text = text + ' `p1.'
  return text
#  _eloquence.speak(text, index)

# def cancel(self):
#  self.dll.eciStop(self.handle)

 def pause(self,switch):
  _eloquence.pause(switch)
#  self.dll.eciPause(self.handle,switch)

 def terminate(self):
  _eloquence.terminate()

 _backquoteVoiceTags=False
 _ABRDICT=False
 def _get_backquoteVoiceTags(self):
  return self._backquoteVoiceTags

 def _set_backquoteVoiceTags(self, enable):
  if enable == self._backquoteVoiceTags:
   return
  self._backquoteVoiceTags = enable
 def _get_ABRDICT(self):
  return self._ABRDICT

 def _set_ABRDICT(self, enable):
  if enable == self._ABRDICT:
   return
  self._ABRDICT = enable

 def _get_rate(self):
  return self._paramToPercent(self.getVParam(_eloquence.rate),minRate,maxRate)

 def _set_rate(self,vl):
  self._rate = self._percentToParam(vl,minRate,maxRate)
  self.setVParam(_eloquence.rate,self._percentToParam(vl,minRate,maxRate))

 def _get_pitch(self):
  return self.getVParam(_eloquence.pitch)

 def _set_pitch(self,vl):
  self.setVParam(_eloquence.pitch,vl)

 def _get_volume(self):
  return self.getVParam(_eloquence.vlm)

 def _set_volume(self,vl):
  self.setVParam(_eloquence.vlm,int(vl))

 def _set_inflection(self,vl):
  vl = int(vl)
  self.setVParam(_eloquence.fluctuation,vl)

 def _get_inflection(self):
  return self.getVParam(_eloquence.fluctuation)

 def _set_hsz(self,vl):
  vl = int(vl)
  self.setVParam(_eloquence.hsz,vl)

 def _get_hsz(self):
  return self.getVParam(_eloquence.hsz)

 def _set_rgh(self,vl):
  vl = int(vl)
  self.setVParam(_eloquence.rgh,vl)

 def _get_rgh(self):
  return self.getVParam(_eloquence.rgh)

 def _set_bth(self,vl):
  vl = int(vl)
  self.setVParam(_eloquence.bth,vl)

 def _get_bth(self):
  return self.getVParam(_eloquence.bth)

 def _getAvailableVoices(self):
  o = OrderedDict()
  for name in os.listdir(_eloquence.eciPath[:-8]):
   if not name.lower().endswith('.syn'): continue
   info = _eloquence.langs[name.lower()[:-4]]
   o[str(info[0])] = synthDriverHandler.VoiceInfo(str(info[0]), info[1], info[2])
  return o

 def _get_voice(self):
  return str(_eloquence.params[9])
 def _set_voice(self,vl):
  _eloquence.set_voice(vl)
  self.curvoice = vl
 def getVParam(self,pr):
  return _eloquence.getVParam(pr)

 def setVParam(self, pr,vl):
  _eloquence.setVParam(pr, vl)

 def _get_lastIndex(self):
#fix?
  return _eloquence.lastindex

 def cancel(self):
  _eloquence.stop()

 def _getAvailableVariants(self):
  global variants
  return OrderedDict((str(id), synthDriverHandler.VoiceInfo(str(id), name)) for id, name in variants.iteritems())

 def _set_variant(self, v):
  global variants
  self._variant = v if int(v) in variants else "1"
  _eloquence.setVariant(int(v))
  self.setVParam(_eloquence.rate, self._rate)
#  if 'eloquence' in config.conf['speech']:
#   config.conf['speech']['eloquence']['pitch'] = self.pitch

 def _get_variant(self): return self._variant

def resub(dct, s):
 for r in dct.keys():
  s = r.sub(dct[r], s)
 return s
