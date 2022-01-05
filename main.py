import os
import hashlib
from database import *
from datetime import datetime
from flask_cors import CORS
from flask_cors.decorator import cross_origin
from flask import Flask, render_template, request, redirect, jsonify


db = DataBase(path=os.path.join(os.getcwd(), "db"), filename="b52.db")
db.create_table(name="users",
                labels={"id": DBType.TEXT,
                        "user_name": DBType.TEXT,
                        "first_name": DBType.TEXT,
                        "last_name": DBType.TEXT,
                        "patronymic": DBType.TEXT,
                        "company_name": DBType.TEXT,
                        "phone": DBType.TEXT,
                        "email": DBType.TEXT,
                        "password": DBType.TEXT},
                primary_key="id")

db.create_table(name="company",
                labels={"id": DBType.TEXT,
                        "admin": DBType.TEXT,
                        "company_name": DBType.TEXT,
                        "employees": DBType.TEXT,
                        "licenses": DBType.INTEGER},
                primary_key="id")

app = Flask(__name__)
CORS(app)
tokens = {}


# =========================================================USER=========================================================
@app.route('/api/login', methods=['POST'])
@cross_origin()
def user_login():
    api_json = request.get_json()
    user = db_get_user(user_id=get_hash(mystring=api_json['email']))
    company = db_get_company(get_hash(user['company_name']))
    if user["password"] != api_json['password']:
        raise Exception("Password is incorrect!")

    token = user["id"] + get_hash(str(datetime.now()))
    tokens[token] = user["id"]
    return jsonify({"token": token,
                    "user": {"id": user["id"],
                             "username": user["user_name"],
                             "first_name": user["first_name"],
                             "second_name": user["last_name"],
                             "patronymic": user["patronymic"],
                             "phone": user["phone"],
                             "userRole": "ADMIN" if user["id"] == company["admin"] else "EMPLOYEE",
                             "company": {"id": get_hash(user["company_name"]),
                                         "name": user["company_name"],
                                         "licenses": company["licenses"]}}})


@app.route('/api/registerUser', methods=['POST'])
@cross_origin()
def register_user():
    api_json = request.get_json()
    user_id = get_hash(api_json['email'])
    company_id = get_hash(api_json['company_name'])
    if user_id in db.get_table("users").get_all_UIDs():
        raise Exception('User already exist!')
    if company_id not in db.get_table("company").get_all_UIDs():
        db_add_company(company_id=company_id,
                       admin=user_id,
                       company_name=api_json['company_name'],
                       employees=user_id,
                       licenses=1)
    else:
        employees = str(db.get_table("company").get_from_cell(key=company_id, column_name="employees")).split(",")
        db.get_table("company").set_to_cell(key=company_id, column_name="employees",
                                            new_value=",".join(employees + [user_id]))
    db_add_user(user_id=user_id,
                user_name=api_json['first_name'],
                first_name=api_json['first_name'],
                second_name=api_json['second_name'],
                patronymic=api_json['patronymic'],
                company_name=api_json['company_name'],
                phone=api_json['phone'],
                email=api_json['email'],
                password=api_json['password'])
    user = db_get_user(user_id=get_hash(mystring=api_json['email']))
    company = db_get_company(get_hash(user['company_name']))
    token = user_id + get_hash(str(datetime.now()))
    tokens[token] = user_id
    return jsonify({"token": token,
                    "user": {"id": user["id"],
                             "username": user["user_name"],
                             "first_name": user["first_name"],
                             "second_name": user["last_name"],
                             "patronymic": user["patronymic"],
                             "phone": user["phone"],
                             "userRole": "ADMIN" if user["id"] == company["admin"] else "EMPLOYEE",
                             "company": {"id": get_hash(user["company_name"]),
                                         "name": user["company_name"],
                                         "licenses": company["licenses"]}}})


@app.route('/api/user/<string:user_id>', methods=['GET'])
@cross_origin()
def get_user(user_id: str):
    if user_id not in db.get_table("users").get_all_UIDs():
        raise Exception('User not founded!')
    user = db_get_user(user_id)
    company = db_get_company(get_hash(user['company_name']))
    return jsonify({"id": user["id"],
                    "username": user["user_name"],
                    "first_name": user["first_name"],
                    "second_name": user["last_name"],
                    "patronymic": user["patronymic"],
                    "phone": user["phone"],
                    "userRole": "ADMIN" if user["id"] == company["admin"] else "EMPLOYEE",
                    "company": {"id": get_hash(user["company_name"]),
                                "name": user["company_name"],
                                "licenses": company["licenses"]}})


@app.route('/api/user/<string:user_id>/changePassword', methods=['POST'])
@cross_origin()
def change_password(user_id: str):
    if user_id not in db.get_table("users").get_all_UIDs():
        raise Exception('User not founded!')
    user = db_get_user(user_id)
    if request.args.get('password') != user["password"]:
        return jsonify({"success": False})
    db.get_table("users").set_to_cell(key=user_id,
                                      column_name="password",
                                      new_value=request.args.get('new_password'))
    return jsonify(success=True)


def db_add_user(user_id: str, user_name: str, first_name: str, second_name: str, patronymic: str, company_name: str,
                phone: str, email: str, password: str) -> None:
    db.get_table("users").add_row(row=[user_id, user_name, first_name, second_name, patronymic,
                                       company_name, phone, email, password])


def db_get_user(user_id: str) -> Dict[str, Any]:
    return {col: user_val for col, user_val in zip(db.get_table("users").get_column_names(),
                                                   db.get_table("users").get_row(key=str(user_id)))}


# =========================================================COMPANY======================================================
@app.route('/api/company/<string:company_id>', methods=['GET'])
@cross_origin()
def get_company_info(company_id: str):
    if company_id not in db.get_table("company").get_all_UIDs():
        raise Exception('Company not founded!')
    company = db_get_company(company_id=company_id)
    return jsonify({"id": company["id"],
                    "name": company["company_name"],
                    "licenses": company["licenses"]})


@app.route('/api/company/<string:company_id>/employees', methods=['GET'])
@cross_origin()
def get_company_employees(company_id: str):
    if company_id not in db.get_table("company").get_all_UIDs():
        raise Exception('Company not founded!')
    items = []
    for employ in db_get_company(company_id=company_id)['employees'].split(","):
        user = db_get_user(user_id=employ)
        items.append({"id": user["id"], "full_name": user["first_name"]})
    return jsonify({items})


@app.route('/api/company/<string:company_id>/registerEmployee', methods=['POST'])
@cross_origin()
def company_register_employee(company_id: str):
    api_json = request.get_json()
    if company_id not in db.get_table("company").get_all_UIDs():
        raise Exception('Company not founded!')
    company = db_get_company(company_id=company_id)['employees'].split(",")
    if get_hash(api_json['email']) in company['employees'].split(","):
        raise Exception("This user already exist")
    db_add_user(user_id=get_hash(api_json['email']),
                user_name=api_json['first_name'],
                first_name=api_json['first_name'],
                second_name=api_json['second_name'],
                patronymic=api_json['patronymic'],
                company_name=company['company_name'],
                phone="8(000) 000-00-00",
                email=api_json['email'],
                password=get_hash(api_json['first_name']))
    db.get_table("company").set_to_cell(key=company_id,
                                        column_name="employees",
                                        new_value=f"{company['employees']},{get_hash(api_json['email'])}")

    return jsonify({"email": api_json['email'],
                    "first_name": api_json['first_name'],
                    "second_name": api_json['second_name'],
                    "patronymic": api_json['patronymic'],
                    "categories": [{} ],
                    "password": get_hash(api_json['first_name'])})


@app.route('/api/company/<string:company_id>/employee/<string:user_id>', methods=['DELETE'])
@cross_origin()
def company_delete_employee(company_id: str, user_id: str):
    if company_id not in db.get_table("company").get_all_UIDs():
        raise Exception('Company not founded!')
    if user_id not in db.get_table("users").get_all_UIDs():
        raise Exception('User not founded!')
    employees = db_get_company(company_id=company_id)['employees'].split(",")
    if user_id not in employees:
        raise Exception('User not founded in this company!')
    employees.remove(user_id)
    db.get_table("company").set_to_cell(key=company_id,
                                        column_name="employees",
                                        new_value=",".join(employees))
    return jsonify({"success": True})


def db_add_company(company_id: str, admin: str, company_name: str, employees: str, licenses: int) -> None:
    db.get_table("company").add_row(row=[company_id, admin, company_name, employees, licenses])


def db_get_company(company_id: str) -> Dict[str, Any]:
    return {col: company_val for col, company_val in zip(db.get_table("company").get_column_names(),
                                                   db.get_table("company").get_row(key=str(company_id)))}


def get_hash(mystring: str) -> str:
    """
    Этот метод на вход получает строку (в нашем часном случае - почту) и хэширует её
    :param mystring: Входная строка
    :return:
    """
    hash_object = hashlib.md5(mystring.encode())
    return hash_object.hexdigest()


if __name__ == '__main__':
    app.run(debug=True)
