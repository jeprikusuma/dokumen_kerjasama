from flask import  Flask, flash, request, send_file, make_response, url_for, render_template
import json, time
import cv2
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import random
import string
import datetime
from werkzeug.utils import secure_filename
import mysql.connector

ALLOWED_EXTENSIONS = set(['pdf'])

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]iasdfffsd/'

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="dokumen_kerjasama"
)
cursor = mydb.cursor()


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# home
@app.route('/', methods=['GET'])
def home():
    return render_template('main.html')

@app.route('/get_data', methods=['GET'])
def get_data():
    keyword = request.args.get('keyword');

    sql = "SELECT \
        dokumen.id AS id, \
        dokumen.judul AS judul, \
        dokumen.jenis AS jenis, \
        dokumen.banner AS banner, \
        validitas.meterai AS meterai, \
        validitas.cap AS cap, \
        validitas.ttd AS ttd \
        FROM dokumen \
        LEFT JOIN validitas ON dokumen.id = validitas.dokumen_id \
        WHERE UPPER(judul) LIKE UPPER(%s)"
    
    args=['%'+keyword+'%']
    cursor.execute(sql,args)
    result = cursor.fetchall()
    json_dump = json.dumps(result)
    return json_dump


@app.route('/check_logo',  methods=['GET'])
def check_logo():
    file = request.files['file']




# detail

@app.route('/detail/<int:id>', methods=['GET'])
def detail(id):
    sql_result = "SELECT \
        dokumen.id AS id, \
        dokumen.judul AS judul, \
        dokumen.jenis AS jenis, \
        dokumen.banner AS banner, \
        dokumen.source AS source, \
        validitas.meterai AS meterai, \
        validitas.cap AS cap, \
        validitas.ttd AS ttd \
        FROM dokumen \
        LEFT JOIN validitas ON dokumen.id = validitas.dokumen_id \
        WHERE dokumen.id = %s"

    id_doc = (id, )
    cursor.execute(sql_result, id_doc)
    result = cursor.fetchone()

    sql_komponen = 'SELECT * FROM komponen WHERE dokumen_id = %s'
    cursor.execute(sql_komponen, id_doc)
    komponen = cursor.fetchall()

    komponen_meterai = [a for a in komponen if a[2] == 'meterai']
    komponen_cap = [a for a in komponen if a[2] == 'cap']
    komponen_ttd = [a for a in komponen if a[2] == 'ttd']

    is_valid = ""
    if(result[5] != None):
        if(result[2] == 'dalam_negeri'):
            if(result[5] >= 1 and result[6] >= 2 and result[7] >= 2):
                is_valid = 'Valid'
            else:
                is_valid = 'Tidak Valid'
        else:
            if(result[6] >= 2 and result[7] >= 2):
                is_valid = 'Valid'
            else:
                is_valid = 'Tidak Valid'
    else:
        is_valid = 'Tidak diketahui'

    return render_template('detail.html', 
                           result = result, 
                           komponen_meterai = komponen_meterai, 
                           komponen_cap = komponen_cap, 
                           komponen_ttd = komponen_ttd, 
                           is_valid = is_valid)

@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    path = os.path.join('static/pdf', filename)
    return send_file(path, as_attachment=True)

# validasi semua
@app.route('/validasi', methods=['GET'])
def validate():
    sql = 'SELECT id FROM dokumen WHERE NOT EXISTS ( SELECT dokumen_id FROM validitas WHERE dokumen.id = validitas.dokumen_id )'
    cursor.execute(sql)
    result = cursor.fetchall()
    return render_template('validate.html', dokumen = len(result))

@app.route('/validasi', methods=['POST'])
def validating():
    sql = 'SELECT id, source FROM dokumen WHERE NOT EXISTS ( SELECT dokumen_id FROM validitas WHERE dokumen.id = validitas.dokumen_id )'
    cursor.execute(sql)
    result = cursor.fetchall()

    for r in result:
        current_db_id = r[0]
        print(current_db_id, 'progress..')

        full_path = os.path.realpath(__file__)
        src_dir = os.path.dirname(full_path)
        file = os.path.join(src_dir, 'static','pdf', r[1])

        if file:

            # Remove files in folder
            # files = glob.glob('static/images/results/*')
            # for fll in files:
            #     os.remove(fll)

            init_page = 1

            # 0. Create FileID & Upload to DB
            dt = datetime.datetime.now()
            seq = int(dt.strftime("%Y%m%d%H%M%S"))
            rand = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5))
            rand_name = str(seq) + rand + '.png'

            # upload ke db
            db_dokumen = "UPDATE dokumen SET banner = %s WHERE id = %s"
            val_dokumen = (rand_name, current_db_id)
            cursor.execute(db_dokumen, val_dokumen)
            mydb.commit()

                
            # 1. Extract PDF 
            import ExtractPDF
            imgs = ExtractPDF.extract_pdf_path(file)
            cv2.imwrite('static/images/covers/'+rand_name, np.asarray(imgs[0]))

            print('Extract PDF done')
            

            while(True):
                print('proccess page ', init_page, '....')

                img = imgs[len(imgs)-init_page]
                
                # 2. Preprocessing
                import Preprocessing
                preprocessed = Preprocessing.preprocessing(img)
                normalized = Preprocessing.normalize(preprocessed, [640, 640])
                print('Preprocessing done')

                # 3. Extract LBP
                import ExtractLBP
                lbp = ExtractLBP.run_lbp(normalized)
                print('Extract LBP done')

                # 4. Extract ROI
                import YOLO
                roi = YOLO.run_model(lbp, 'roi.pt')
                coor_roi = YOLO.coordinate_box(roi, preprocessed)

                # if not include roi
                if(len(coor_roi) == 0):
                    init_page = init_page + 1
                    continue
                
                # chceck duplicate
                left = [a for a in coor_roi if a[0] == 0]
                left_max = 0
                left_result = []
                for a in left:
                    if(a[5] > left_max):
                        left_max = a[5]
                        left_result = a

                right = [a for a in coor_roi if a[0] == 1]
                right_max = 0
                right_result = []
                for a in right:
                    if(a[5] > right_max):
                        right_max = a[5]
                        right_result = a
            
                coor_roi = []
                if(len(left_result) > 0):
                    coor_roi.append(left_result)
                if(len(right_result) > 0):
                    coor_roi.append(right_result)

                # 5. Ekstract Component
                img = np.asarray(img)
                img_copy = img.copy()
                result = []
                ttd_files = []
                count_ttd = 0
                cap_files = []
                count_cap = 0
                count_meterai = 0
                meterai_files = []

                for c in coor_roi:
                    clp, lp, tp, rp, bp, pp = c
                    lp = lp - 35
                    tp = tp - 45
                    rp = rp + 35
                    bp = bp + 45
                    x_shape, y_shape = preprocessed.shape[1], preprocessed.shape[0]
                    if(lp < 0):
                        lp = 0
                    if(tp < 0):
                        tp = 0
                    if(rp > x_shape):
                        rp = x_shape
                    if(bp > y_shape):
                        bp = y_shape
                    img_part = preprocessed[tp:bp, lp:rp]
                    comp = YOLO.run_model(img_part, 'component.pt')
                    coor_comp = YOLO.coordinate_box(comp, img_part)
                    
                    # chceck duplicate
                    ttd = [a for a in coor_comp if a[0] == 0]
                    ttd_max = 0
                    ttd_result = []
                    for a in ttd:
                        if(a[5] > ttd_max):
                            ttd_max = a[5]
                            ttd_result = a

                    cap = [a for a in coor_comp if a[0] == 1]
                    cap_max = 0
                    cap_result = []
                    for a in cap:
                        if(a[5] > cap_max):
                            cap_max = a[5]
                            cap_result = a

                    meterai = [a for a in coor_comp if a[0] == 2]
                    meterai_max = 0
                    meterai_result = []
                    for a in meterai:
                        if(a[5] > meterai_max):
                            meterai_max = a[5]
                            meterai_result = a
                    
                    coor_comp = []
                    if(len(ttd_result) > 0):
                        coor_comp.append(ttd_result)
                    if(len(cap_result) > 0):
                        coor_comp.append(cap_result)
                    if(len(meterai_result) > 0):
                        coor_comp.append(meterai_result)
                    # 6. Rebuild
                    for k in coor_comp:
                        cl, l, t, r, b, p = k
                        
                        l = l + lp
                        t = t + tp
                        r = r + lp
                        b = b +  tp

                        if cl == 0:
                            cv2.rectangle(img, (l, t), (r, b), (255, 0, 0), 2)
                            cl_name = str(seq) + rand + str(int(clp)) + '.meterai' + '.png'
                            meterai_files.append(cl_name)
                            count_meterai = count_meterai + 1
                            result.append('meterai')
                            # save to db
                            in_komponen = "INSERT INTO komponen (dokumen_id, komponen, source) VALUES (%s, %s, %s)"
                            val_komponen = (current_db_id, 'meterai', cl_name)
                            cursor.execute(in_komponen, val_komponen)
                            mydb.commit()
                        elif cl == 1:
                            cv2.rectangle(img, (l, t), (r, b), (0, 0, 255), 2)
                            cl_name = str(seq) + rand + str(int(clp)) + '.cap' + '.png'
                            cap_files.append(cl_name)
                            count_cap = count_cap + 1
                            result.append('cap')
                            # save to db
                            in_komponen = "INSERT INTO komponen (dokumen_id, komponen, source) VALUES (%s, %s, %s)"
                            val_komponen = (current_db_id, 'cap', cl_name)
                            cursor.execute(in_komponen, val_komponen)
                            mydb.commit()
                        else:
                            result.append('ttd')
                            count_ttd = count_ttd + 1
                            cl_name = str(seq) + rand + str(int(clp)) + '.ttd' + '.png'
                            ttd_files.append(cl_name)
                            cv2.rectangle(img, (l, t), (r, b), (0, 255, 0), 2)
                            # save to db
                            in_komponen = "INSERT INTO komponen (dokumen_id, komponen, source) VALUES (%s, %s, %s)"
                            val_komponen = (current_db_id, 'ttd', cl_name)
                            cursor.execute(in_komponen, val_komponen)
                            mydb.commit()

                        component_rest = img_copy[t:b, l:r]
                        cv2.imwrite('static/images/results/'+cl_name, component_rest)
                
                
                cv2.imwrite('static/images/results/'+rand_name, img)

                # save to db
                in_validitas = "INSERT INTO validitas (meterai, cap, ttd, dokumen_id) VALUES (%s, %s, %s, %s)"
                val_validitas = (count_meterai, count_cap, count_ttd, current_db_id)
                cursor.execute(in_validitas, val_validitas)
                mydb.commit()

                # return value
                break

        else:
            data_set = {'status': 'false'}
            json_dump = json.dumps(data_set)
            return json_dump
    
    json_dump = json.dumps(result)
    return json_dump

# upload
@app.route('/upload', methods=['GET'])
def upload_index():
    return render_template('add.html')

@app.route('/upload', methods=['POST'])
def upload():
    form_judul = request.form.get("judul")
    form_jenis = request.form.get("jenis")

    if(form_judul == None or form_jenis == None):
        data_set = {'status': 'no data'}
        json_dump = json.dumps(data_set)
        return json_dump
    
    if 'file' not in request.files:
        data_set = {'status': 'no data'}
        json_dump = json.dumps(data_set)
        return json_dump

    file = request.files['file']
    if file and allowed_file(file.filename):

        # Remove files in folder
        # files = glob.glob('static/images/results/*')
        # for fll in files:
        #     os.remove(fll)

        init_page = 1

        # 0. Create FileID & Upload to DB
        dt = datetime.datetime.now()
        seq = int(dt.strftime("%Y%m%d%H%M%S"))
        rand = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=5))
        rand_name = str(seq) + rand + '.png'
        # save file
        filename = secure_filename(file.filename)
        file.save(os.path.join('static/pdf', filename))
        # crate path 
        full_path = os.path.realpath(__file__)
        src_dir = os.path.dirname(full_path)
        new_file = os.path.join(src_dir, 'static','pdf', filename)

        # upload ke db
        db_dokumen = "INSERT INTO dokumen (judul, jenis, banner, source) VALUES (%s, %s, %s, %s)"
        val_dokumen = (form_judul, form_jenis, rand_name, filename)
        cursor.execute(db_dokumen, val_dokumen)
        mydb.commit()

        cursor.execute("SELECT last_insert_id()")
        current_db_id = cursor.fetchall()[0][0]
              
        # 1. Extract PDF 
        import ExtractPDF
        imgs = ExtractPDF.extract_pdf_path(new_file)
        cv2.imwrite('static/images/covers/'+rand_name, np.asarray(imgs[0]))

        print('Extract PDF done')
        

        while(True):
            print('proccess page ', init_page, '....')

            img = imgs[len(imgs)-init_page]
            
            
            # 2. Preprocessing
            import Preprocessing
            preprocessed = Preprocessing.preprocessing(img)
            normalized = Preprocessing.normalize(preprocessed, [640, 640])
            print('Preprocessing done')

            # 3. Extract LBP
            import ExtractLBP
            lbp = ExtractLBP.run_lbp(normalized)
            print('Extract LBP done')

            # 4. Extract ROI
            import YOLO
            roi = YOLO.run_model(lbp, 'roi.pt')
            coor_roi = YOLO.coordinate_box(roi, preprocessed)

            # if not include roi
            if(len(coor_roi) == 0):
                init_page = init_page + 1
                continue
            
            # chceck duplicate
            left = [a for a in coor_roi if a[0] == 0]
            left_max = 0
            left_result = []
            for a in left:
                if(a[5] > left_max):
                    left_max = a[5]
                    left_result = a

            right = [a for a in coor_roi if a[0] == 1]
            right_max = 0
            right_result = []
            for a in right:
                if(a[5] > right_max):
                    right_max = a[5]
                    right_result = a
           
            coor_roi = []
            if(len(left_result) > 0):
                coor_roi.append(left_result)
            if(len(right_result) > 0):
                coor_roi.append(right_result)

            # 5. Ekstract Component
            img = np.asarray(img)
            img_copy = img.copy()
            result = []
            ttd_files = []
            count_ttd = 0
            cap_files = []
            count_cap = 0
            count_meterai = 0
            meterai_files = []

            for c in coor_roi:
                clp, lp, tp, rp, bp, pp = c
                lp = lp - 35
                tp = tp - 45
                rp = rp + 35
                bp = bp + 45
                x_shape, y_shape = preprocessed.shape[1], preprocessed.shape[0]
                if(lp < 0):
                    lp = 0
                if(tp < 0):
                    tp = 0
                if(rp > x_shape):
                    rp = x_shape
                if(bp > y_shape):
                    bp = y_shape
                img_part = preprocessed[tp:bp, lp:rp]
                comp = YOLO.run_model(img_part, 'component.pt')
                coor_comp = YOLO.coordinate_box(comp, img_part)
                
                # chceck duplicate
                ttd = [a for a in coor_comp if a[0] == 0]
                ttd_max = 0
                ttd_result = []
                for a in ttd:
                    if(a[5] > ttd_max):
                        ttd_max = a[5]
                        ttd_result = a

                cap = [a for a in coor_comp if a[0] == 1]
                cap_max = 0
                cap_result = []
                for a in cap:
                    if(a[5] > cap_max):
                        cap_max = a[5]
                        cap_result = a

                meterai = [a for a in coor_comp if a[0] == 2]
                meterai_max = 0
                meterai_result = []
                for a in meterai:
                    if(a[5] > meterai_max):
                        meterai_max = a[5]
                        meterai_result = a
                
                coor_comp = []
                if(len(ttd_result) > 0):
                    coor_comp.append(ttd_result)
                if(len(cap_result) > 0):
                    coor_comp.append(cap_result)
                if(len(meterai_result) > 0):
                    coor_comp.append(meterai_result)
                # 6. Rebuild
                for k in coor_comp:
                    cl, l, t, r, b, p = k
                    
                    l = l + lp
                    t = t + tp
                    r = r + lp
                    b = b +  tp

                    if cl == 0:
                        cv2.rectangle(img, (l, t), (r, b), (255, 0, 0), 2)
                        cl_name = str(seq) + rand + str(int(clp)) + '.meterai' + '.png'
                        meterai_files.append(cl_name)
                        count_meterai = count_meterai + 1
                        result.append('meterai')
                        # save to db
                        in_komponen = "INSERT INTO komponen (dokumen_id, komponen, source) VALUES (%s, %s, %s)"
                        val_komponen = (current_db_id, 'meterai', cl_name)
                        cursor.execute(in_komponen, val_komponen)
                        mydb.commit()
                    elif cl == 1:
                        cv2.rectangle(img, (l, t), (r, b), (0, 0, 255), 2)
                        cl_name = str(seq) + rand + str(int(clp)) + '.cap' + '.png'
                        cap_files.append(cl_name)
                        count_cap = count_cap + 1
                        result.append('cap')
                        # save to db
                        in_komponen = "INSERT INTO komponen (dokumen_id, komponen, source) VALUES (%s, %s, %s)"
                        val_komponen = (current_db_id, 'cap', cl_name)
                        cursor.execute(in_komponen, val_komponen)
                        mydb.commit()
                    else:
                        result.append('ttd')
                        count_ttd = count_ttd + 1
                        cl_name = str(seq) + rand + str(int(clp)) + '.ttd' + '.png'
                        ttd_files.append(cl_name)
                        cv2.rectangle(img, (l, t), (r, b), (0, 255, 0), 2)
                        # save to db
                        in_komponen = "INSERT INTO komponen (dokumen_id, komponen, source) VALUES (%s, %s, %s)"
                        val_komponen = (current_db_id, 'ttd', cl_name)
                        cursor.execute(in_komponen, val_komponen)
                        mydb.commit()

                    component_rest = img_copy[t:b, l:r]
                    cv2.imwrite('static/images/results/'+cl_name, component_rest)
            
            
            cv2.imwrite('static/images/results/'+rand_name, img)

            # save to db
            in_validitas = "INSERT INTO validitas (meterai, cap, ttd, dokumen_id) VALUES (%s, %s, %s, %s)"
            val_validitas = (count_meterai, count_cap, count_ttd, current_db_id)
            cursor.execute(in_validitas, val_validitas)
            mydb.commit()

            img_logo = imgs[0]

            # return value
            return json.dumps({
                'filename': rand_name,
                'label': result,
                'ttds': ttd_files,
                'caps': cap_files,
                'meterais': meterai_files,
            })
            break

    else:
        data_set = {'status': 'false'}
    json_dump = json.dumps(data_set)

    return json_dump
    
    
if __name__ == "__main__":
    app.run(debug=True)