# 使い方

ssh接続でraspiを動かすアプリ

# 0. clone file

# 1. SSH接続情報を入力
コード内の

    self.hostname = "XXXX"

    self.username = "XXXX"

    self.password = "XXXX"
  に自身のsshの情報を入力

# 2. Connectボタンを押しssh接続を開始する
Connectボタンを押すことでssh接続が開始される

ssh接続されていない時ではコードを実行することはできません

# 3. Select Dirボタンで実行したいファイルのあるディレクトリを選択しツリー状のビューでファイルを選択

Select Dirでディレクトリを選んだ後に画面左側にツリー状のファイルビューが展開される

その後実行したいファイルをクリックすると選択状態になる

# 4. Runボタンを押しファイルを実行

Runボタンを押すことで選択されたファイルを実行できる

# 5. Stopボタンを押し実行を止める


