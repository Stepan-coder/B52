import os
import hashlib
from database import *
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


# =========================================================USER=========================================================
@app.route('/api/login', methods=['POST'])
def user_login():
    email = request.args.get('email')
    password = request.args.get('password')
    user = {col: user_val for col, user_val in zip(db.get_table("users").get_column_names(),
                                                   db.get_table("users").get_row(key=get_hash(mystring=email)))}
    if user["password"] != password:
        raise Exception("Password is incorrect!")
    return jsonify({"id": user["id"],
                    "username": user["user_name"],
                    "first_name": user["first_name"],
                    "second_name": user["last_name"],
                    "patronymic": user["patronymic"],
                    "phone": user["phone"]})


@app.route('/api/registerUser', methods=['POST'])
def register_user():
    user_id = get_hash(request.args.get('email'))
    company_id = get_hash(request.args.get('company_name'))
    if user_id in db.get_table("users").get_all_UIDs():
        raise Exception('User already exist!')
    if company_id not in db.get_table("company").get_all_UIDs():
        db_add_company(company_id=company_id,
                       admin=user_id,
                       company_name=request.args.get('company_name'),
                       employees=user_id,
                       licenses=1)
    else:
        employees = str(db.get_table("company").get_from_cell(key=company_id, column_name="employees")).split(",")
        db.get_table("company").set_to_cell(key=company_id, column_name="employees",
                                            new_value=",".join(employees + [user_id]))
    db_add_user(user_id=user_id,
                user_name=request.args.get('first_name'),
                first_name=request.args.get('first_name'),
                second_name=request.args.get('second_name'),
                patronymic=request.args.get('patronymic'),
                company_name=request.args.get('company_name'),
                phone=request.args.get('phone'),
                email=request.args.get('email'),
                password=request.args.get('password'))

    return jsonify({"id": user_id,
                    "username": request.args.get('first_name'),
                    "first_name": request.args.get('first_name'),
                    "second_name": request.args.get('second_name'),
                    "patronymic": request.args.get('patronymic'),
                    "phone": request.args.get('phone')})


@app.route('/api/user/<string:user_id>', methods=['GET'])
def get_user(user_id: str):
    if user_id not in db.get_table("users").get_all_UIDs():
        raise Exception('User not founded!')
    user = db_get_user(user_id)
    return jsonify({"id": user["id"],
                    "username": user["user_name"],
                    "first_name": user["first_name"],
                    "second_name": user["last_name"],
                    "patronymic": user["patronymic"],
                    "phone": user["phone"]})


@app.route('/api/user/<string:user_id>/changePassword', methods=['POST'])
def change_password(user_id: str):
    if user_id not in db.get_table("users").get_all_UIDs():
        raise Exception('User not founded!')
    user = db_get_user(user_id)
    if request.args.get('password') != user["password"]:
        return jsonify({"success": False})
    db.get_table("users").set_to_cell(key=user_id,
                                      column_name="password",
                                      new_value=request.args.get('new_password'))
    return jsonify({"success": True})


def db_add_user(user_id: str, user_name: str, first_name: str, second_name: str, patronymic: str, company_name: str,
                phone: str, email: str, password: str) -> None:
    db.get_table("users").add_row(row=[user_id, user_name, first_name, second_name, patronymic,
                                       company_name, phone, email, password])


def db_get_user(user_id: str) -> Dict[str, Any]:
    return {col: user_val for col, user_val in zip(db.get_table("users").get_column_names(),
                                                   db.get_table("users").get_row(key=str(user_id)))}


# =========================================================COMPANY======================================================
@app.route('/api/company/<string:company_id>', methods=['GET'])
def get_company_info(company_id: str):
    if company_id not in db.get_table("company").get_all_UIDs():
        raise Exception('Company not founded!')
    company = db_get_company(company_id=company_id)
    return jsonify({"id": company["id"],
                    "name": company["company_name"],
                    "licenses": company["licenses"]})


@app.route('/api/company/<string:company_id>/employees', methods=['GET'])
def get_company_employees(company_id: str):
    if company_id not in db.get_table("company").get_all_UIDs():
        raise Exception('Company not founded!')
    items = []
    for employ in db_get_company(company_id=company_id)['employees'].split(","):
        user = db_get_user(user_id=employ)
        items.append({"id": user["id"], "full_name": user["first_name"]})
    return jsonify({items})


@app.route('/api/company/<string:company_id>/employee/<string:user_id>', methods=['DELETE'])
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

# /api/company/{companyId}/registerEmployee


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
