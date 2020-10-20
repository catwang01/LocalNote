import pytest
import pexpect


class TestCase():

    def test_1_init(self):
        token = "S=s54:U=157132c:E=16bd2587947:C=16bae4bf530:P=1cd:A=en-devtoken:V=2:H=e9d6084e80270661c8fdd80fca2896b9"
        root_path = "/Users/ed/Git/LocalNote/LocalNote/test/evernote"
        main_path = "/Users/ed/Git/LocalNote/LocalNote/main.py"
        cmd = "cd {} && python {} init".format(root_path, main_path)
        child = pexpect.spawn(cmd)
        child.expect("是否是沙盒环境？")
        child.sendline('y')
        child.expect('是否使用开发者Token？')
        child.sendline('y')
        child.expect('开发者Token:')
        child.sendline(token)


if __name__ == "__main__":
    pytest.main(["-s"])
