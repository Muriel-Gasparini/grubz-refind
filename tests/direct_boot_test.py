import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('direct',pathlib.Path(__file__).resolve().parents[1]/'grubz/direct_boot.py')
direct=importlib.util.module_from_spec(spec);spec.loader.exec_module(direct)

class UpdateTests(unittest.TestCase):
 def test_numeric_kernel_order_and_incomplete_pair(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for v in ['6.1.0-9-amd64','6.1.0-54-amd64','6.1.0-100-amd64']:
    (p/('vmlinuz-'+v)).write_bytes(b'kernel')
   for v in ['6.1.0-9-amd64','6.1.0-54-amd64']:
    (p/('initrd.img-'+v)).write_bytes(b'initrd')
   self.assertEqual(direct.latest_kernel(p),'6.1.0-54-amd64')
 def test_failed_build_keeps_current_and_previous(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'current.efi').write_bytes(b'old');(p/'previous.efi').write_bytes(b'older')
   def fail(target):
    target.write_bytes(b'partial');raise RuntimeError('signing failed')
   with self.assertRaises(RuntimeError):direct.publish(p,fail,lambda _:None)
   self.assertEqual((p/'current.efi').read_bytes(),b'old')
   self.assertEqual((p/'previous.efi').read_bytes(),b'older')
 def test_rejected_signature_keeps_current(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'current.efi').write_bytes(b'old')
   def reject(_):raise RuntimeError('invalid signature')
   with self.assertRaises(RuntimeError):direct.publish(p,lambda x:x.write_bytes(b'new'),reject)
   self.assertEqual((p/'current.efi').read_bytes(),b'old')
 def test_success_keeps_rollback(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'current.efi').write_bytes(b'old')
   direct.publish(p,lambda x:x.write_bytes(b'new'),lambda _:None)
   self.assertEqual((p/'current.efi').read_bytes(),b'new')
   self.assertEqual((p/'previous.efi').read_bytes(),b'old')
 def test_same_payload_does_not_replace_previous(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'current.efi').write_bytes(b'new');(p/'previous.efi').write_bytes(b'old')
   direct.publish(p,lambda x:x.write_bytes(b'new'),lambda _:None)
   self.assertEqual((p/'previous.efi').read_bytes(),b'old')

 def test_unmounted_esp_refuses_publish(self):
  with tempfile.TemporaryDirectory() as d:
   cfg={'esp':d,'esp_uuid':'correct'}
   with patch.object(direct,'run',return_value='{"filesystems":[{"target":"/","fstype":"ext4","uuid":"wrong"}]}'):
    with self.assertRaises(RuntimeError): direct.update(cfg)
   self.assertFalse((pathlib.Path(d)/'EFI').exists())
 def test_no_complete_kernel_refused(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(RuntimeError): direct.latest_kernel(d)
 def test_out_of_space_preserves_current(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for n in ('vmlinuz-6.1.0-54-amd64','initrd.img-6.1.0-54-amd64'): (p/n).write_bytes(b'x')
   cfg={'esp':d,'esp_uuid':'correct','boot':d}
   m=direct.json.dumps({'filesystems':[{'target':d,'fstype':'vfat','uuid':'correct'}]})
   with patch.object(direct,'run',return_value=m), patch.object(direct.shutil,'disk_usage',return_value=type('Usage',(),{'free':0})()):
    with self.assertRaises(RuntimeError): direct.update(cfg)
   self.assertFalse((p/'EFI').exists())

 def test_removing_newest_selects_remaining_kernel(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   for v in ('6.1.0-53-amd64','6.1.0-54-amd64'):
    (p/('vmlinuz-'+v)).write_bytes(b'k');(p/('initrd.img-'+v)).write_bytes(b'i')
   self.assertEqual(direct.latest_kernel(p),'6.1.0-54-amd64')
   (p/'vmlinuz-6.1.0-54-amd64').unlink();(p/'initrd.img-6.1.0-54-amd64').unlink()
   self.assertEqual(direct.latest_kernel(p),'6.1.0-53-amd64')

if __name__=='__main__':unittest.main()
