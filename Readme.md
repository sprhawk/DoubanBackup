豆瓣备份 0.01
============

使用方法
-----
0. 设置自己的api key, 这些信息从 http://developers.douban.com/ 获得，别忘记把自己的帐号加到测试帐号里
   编辑keys.py

   		API_KEY = ""
   		SECRET = ""
   		REDIRECT_URI = ""

1. 授权用户获取access token

   		./doubanbk.py auth

 	会打开默认的浏览器，选择授权之后，会跳到自己指定的callback地址上，带有一个code=xxxxx，在下一步里使用
 		
 		./doubanbk.py token xxxxx
 		
2. 备份自己的所有广播

		./doubanbk.py get shuo
		
