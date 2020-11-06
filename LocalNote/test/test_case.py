import pytest
import os
import sys
import pexpect


class TestCase():

    root_path = "/Users/ed/Git/LocalNote/LocalNote/test/evernote"
    main_path = "/Users/ed/Git/LocalNote/LocalNote/main.py"
    notebooks = ["Test1", "Test2", "Test3"]

    # def test_1_init_sand(self):
    #     token = "S=s1:U=1df:E=1756f72a49a:C=1754b661e28:P=1cd:A=en-devtoken:V=2:H=6a382019f0c12965f7bb03869d7b1e7d"
    #
    #     cmd = "/bin/bash -c 'python {} init'".format(self.main_path)
    #     child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
    #     index = child.expect(["账户仅需要在第一次使用时设置一次", "已经登录", "初始化目录将会清除目录下所有文件"])
    #     while index != 0:
    #         child.sendline('y')
    #         child.expect_exact("初始化目录将会清除目录下所有文件，是否继续？[yn]")
    #         child.sendline('y')
    #         index = child.expect(["账户仅需要在第一次使用时设置一次", "已经登录"])
    #     child.expect("沙盒")
    #     child.sendline('y')
    #     child.expect("是否使用开发者Token")
    #     child.sendline('y')
    #     child.expect("开发者Token:")
    #     child.sendline(token)
    #     assert child.expect("登陆成功") == 0
    #     while True:
    #         index = child.expect(pexpect.EOF)
    #         if index == 0:
    #             break
    #     return

    # def test_1_init(self):
    #     token = "S=s54:U=157132c:E=1755eebc116:C=1753adf3cb0:P=1cd:A=en-devtoken:V=2:H=b1e835e67f6314373ab3677755d3c61f"
    #
    #     cmd = "/bin/bash -c 'python {} init'".format(self.main_path)
    #     child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
    #
    #     possible_outputs = ["账户仅需要在第一次使用时设置一次",  # 0
    #                         "已经登录",     # 1
    #                         "初始化目录将会清除目录下所有文件，是否继续？",  # 2
    #                         "国际",  # 3
    #                         "沙盒",  # 4
    #                         "是否使用开发者Token", # 5
    #                         '开发者Token:', # 6
    #                         "登陆成功", # 7
    #                         ]
    #     while True:
    #         index = child.expect(possible_outputs)
    #         if index in [1, 2, 5]:
    #             child.sendline('y')
    #         elif index in [3, 4]:
    #             child.sendline('n')
    #         elif index == 7:
    #             break
    #         elif index == 6:
    #             child.sendline(token)
    #     while True:
    #         index = child.expect(pexpect.EOF)
    #         if index == 0:
    #             break
    #     return
    #
    # def test_2_notebook(self):
    #     cmd = "/bin/bash -c 'python {} notebook'".format(self.main_path)
    #
    #     child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
    #     child.expect('留空结束')
    #     i = 0
    #     while i < len(self.notebooks):
    #         child.expect_exact('>')
    #         child.sendline(self.notebooks[i])
    #         i += 1
    #     child.expect('>')
    #     child.sendline("")
    #     assert child.expect_exact("[INFO] 修改成功") == 0
    #     while True:
    #         if child.expect(pexpect.EOF) == 0:
    #             break
    #
    # def test_3_pull(self):
    #     cmd = "/bin/bash -c 'python {} pull'".format(self.main_path)
    #
    #     child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
    #     while True:
    #         index = child.expect(["PULL", "更新"])
    #         if index == 1:
    #             child.sendline("y")
    #             break
    #     while True:
    #         index = child.expect(['Downloading', pexpect.EOF])
    #         if index == 1:
    #             break
    #
    #     for notebook in self.notebooks:
    #         assert os.path.exists(os.path.join(self.root_path, notebook))

    def test_4_push_modify(self):
        notebookpath = os.path.join(self.root_path, "Test2")
        first_file = os.listdir(notebookpath)[0]
        with open(os.path.join(notebookpath, first_file), "a") as f:
            f.write("hhhhhhhhhhhaha\n")

        cmd = "/bin/bash -c 'python {} push'".format(self.main_path)

        child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
        child.expect_exact("是否上传本地文件？[yn]")
        child.sendline('y')
        assert child.expect("Uploading") == 0
        while child.expect(pexpect.EOF) != 0:
            pass

    def test_4_push_create(self):
        notebookpath = os.path.join(self.root_path, "Test2")
        new_file_name = "hehe.md"
        with open(os.path.join(notebookpath, new_file_name), "w") as f:
            f.write("hhhhhhhhhhhaha\n")

        cmd = "/bin/bash -c 'python {} push'".format(self.main_path)

        child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
        child.expect_exact("是否上传本地文件？[yn]")
        child.sendline('y')
        assert child.expect("Uploading") == 0
        while child.expect(pexpect.EOF) != 0:
            pass
        os.remove(os.path.join(notebookpath, new_file_name))

    def test_4_push_delete(self):
        notebookpath = os.path.join(self.root_path, "Test2")
        first_file = os.listdir(notebookpath)[0]
        os.remove(os.path.join(notebookpath, first_file))

        cmd = "/bin/bash -c 'python {} push'".format(self.main_path)

        child = pexpect.spawn(cmd, encoding='utf-8', logfile=sys.stdout, cwd=self.root_path)
        child.expect_exact("是否上传本地文件？[yn]")
        child.sendline('y')
        assert child.expect("Uploading") == 0, "Deleted filed not uploaded!"
        while child.expect(pexpect.EOF) != 0:
            pass


if __name__ == "__main__":
    pytest.main(["-s"])
