import gdown
from flask import Flask, render_template, request, redirect, jsonify
import torch
from PIL import Image
import io
import argparse
from flask_cors import CORS
import pymysql
import dbconfig
import json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
CORS(app)

###구글 드라이브에서 가중치 파일 받는 것 추가 테스트 땐 한번 받고 주석처리
# google_path = 'https://drive.google.com/uc?id='
# file_id = '1-bEBxnujEU-R-p29-QM8eFFeRICwjYey'
# output_name = 'best.pt'
# gdown.download(google_path+file_id, output_name,quiet=False)
####e


def get_result(dbname, areaId, categoryId):
    print(type(areaId))
    print(type(categoryId))
    if dbname != dbconfig.DATABASE_CONFIG['dbname']:
        raise ValueError("Could not find DB with given name")
    conn = pymysql.connect(host=dbconfig.DATABASE_CONFIG['host'],
                           user=dbconfig.DATABASE_CONFIG['user'],
                           password=dbconfig.DATABASE_CONFIG['password'],
                           db=dbconfig.DATABASE_CONFIG['dbname'])
    cursor = conn.cursor()
    sql = '''
    SELECT r.price, r.standard, r.description, c.category_name, a.area_name, a.url, a.telephone
    FROM result AS r
    JOIN category AS c ON c.category_id=r.category_id
    JOIN area AS a ON a.area_id=r.area_id
    WHERE a.area_id = %s and c.category_id = %s;
    '''
    cursor.execute(sql, (areaId, categoryId))
    result = cursor.fetchall()
    conn.close()
    return result


@app.route("/service", methods=["GET", "POST"])
def predict():
    print("지역구 :", request.form.get('areaId'))
    print("사용자 :", request.form.get('userId'))
    if request.method == 'POST':
        areaId = int(request.form.get('areaId'))
        if "mainFile" not in request.files:
            return redirect(request.url)
        file = request.files["mainFile"]
        print(file)

    #########################################################################
     # yolo에서 보내주는 값 json 으로 받음 기본설정이라 안건드림
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        results = model(img, size=640)

        results.render()  # updates results.imgs with boxes and labels
        for img in results.imgs:
            img_base64 = Image.fromarray(img)
            img_base64.save("static/result0.jpg", format="JPEG")

        data = results.pandas().xyxy[0].to_json(orient="records")
    ########################################################################


        info_list = list()
              
        # 파싱을 위해 리스트로 바꾸어서 파싱
        list_data = json.loads(data)
        # 클래스 명이 리스트로 저장 (detect 된 종류가 여려개면 여러개 순서로)
        class_id=set()
        for x in list_data:
            class_id.add(x['class'])
        class_id = list(class_id)
        
        if not class_id:
            print("Can't find object")
            infos = "Can't find object"

        else:
         # db 찾아서 출력 어떻게 띄우지
            for c in class_id:
                categoryId = c
                print(categoryId)
                infos = get_result('tracycle', areaId, categoryId)
                for info in infos:
                    info_list.append(info)
                print(infos)

    return jsonify(info_list)



@app.route("/img", methods=["GET", "POST"])
def show():
    if request.method == 'GET':
        print('GET')
        link = "static/result0.jpg"
        print(link)
    return jsonify(link)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Flask app exposing yolov5 models")
    parser.add_argument("--port", default=8085, type=int, help="port number")
    args = parser.parse_args()

    model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt').autoshape()  # force_reload = recache latest code
    model.eval()
    # debug=True causes Restarting with stat
    app.run(host="0.0.0.0", port=args.port)
