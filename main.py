from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import BaseModel
from bs4 import BeautifulSoup
import sqlite3
import aiohttp
import asyncio
import time
from datetime import datetime


class Timer:
    def __init__(self, programnm):
        self.programnm = programnm

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time
        print(f"{self.programnm} Execution time: {self.execution_time:.2f} seconds")


app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    # Add your frontend URL here
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class CourseQuery(BaseModel):
    year: str
    semester: str
    crsid: str = ""
    crsclass: str = ""
    crsnm: str = ""
    is_all_eng: str = ""
    is_dis_learn: str = ""
    crslimit: str = ""
    tchnm: str = ""
    week: str = ""


def gen_search_res(res):
    keys = [
        "查詢序號",
        "學年度",
        "學期",
        "序號",
        "課程代碼",
        "開課班別",
        "課程名稱",
        "教學大綱",
        "課程性質",
        "課程性質2",
        "全英語授課",
        "學分",
        "教師姓名",
        "上課大樓",
        "上課教室",
        "上限人數",
        "登記人數",
        "選上人數",
        "可跨班",
        "備註",
    ]
    search_res = []
    for res_each in range(0, len(res)):
        search_res_each = {key: value for key,
                           value in zip(keys, res[res_each])}
        search_res.append(search_res_each)
    return search_res


async def load_into_db(year="112", semester="2"):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://webap0.ncue.edu.tw/DEANV2/Other/OB010",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            data=f"sel_cls_branch=D&sel_scr_english=&sel_SCR_IS_DIS_LEARN=&sel_yms_year={year}&sel_yms_smester={semester}&scr_selcode=&sel_cls_id=&sel_sct_week=&sub_name=&emp_name=&X-Requested-With=XMLHttpRequest",
        ) as response:
            html_data = await response.text()
            day_course_rows = BeautifulSoup(
                html_data, "html.parser").find_all("tr")

            th_row = day_course_rows[0].find_all("th")

            conn = sqlite3.connect("database.sqlite3")
            c = conn.cursor()

            print(f"load_into_db {year}-{semester} start.")

            c.execute(
                f"DELETE FROM courses WHERE 學年度={year} AND 學期={semester}")

            for i in range(1, len(day_course_rows)):
                columns_row = day_course_rows[i].find_all("td")
                data_dict = {}
                data_dict["學年度"] = year
                data_dict["學期"] = semester
                for th, td in zip(th_row, columns_row):
                    if th.text.strip() == "上課節次+地點":
                        data_dict["上課節次地點"] = td.text.strip()
                    elif th.text.strip() == "開課班別(代表)":
                        data_dict["開課班別"] = td.text.strip()
                    else:
                        data_dict[th.text.strip()] = td.text.strip()

                columns = ", ".join(data_dict.keys())

                # print(columns)
                # print("\n\n", len(data_dict))

                placeholders = ", ".join(["?"] * len(data_dict))

                # print()
                # print(data_dict)

                insert_sql = f"INSERT OR IGNORE INTO courses ({columns}) VALUES ({placeholders})"
                c.execute(insert_sql, list(data_dict.values()))

                # update_sql = f"UPDATE courses SET 學年度={year}, 學期={semester} WHERE 課程代碼=課程代碼;"
                # c.execute(update_sql)

            conn.commit()
            conn.close()
            print(f"load_into_db {year}-{semester} done.")


@app.get("/")
async def read_root():
    return {"message": "Welcome to Course Query API!"}


@app.post("/query/")
async def query_courses(course_query: CourseQuery):
    res = await selectdb(
        year=course_query.year,
        semester=course_query.semester,
        crsid=course_query.crsid,
        crsclass=course_query.crsclass,
        crsnm=course_query.crsnm,
        is_all_eng=course_query.is_all_eng,
        is_dis_learn=course_query.is_dis_learn,
        crslimit=course_query.crslimit,
        tchnm=course_query.tchnm,
        week=course_query.week,
    )
    return {"courses": res}


async def selectdb(
    year="112",
    semester="2",
    crsid="",
    crsclass="",
    crsnm="",
    is_all_eng="",
    is_dis_learn="",
    crslimit="",
    tchnm="",
    week="",
):
    conn = sqlite3.connect("database.sqlite3")
    cursor = conn.cursor()
    query = """
        SELECT
        ROW_NUMBER() OVER (ORDER BY 序號) AS 查詢序號,
        *
        FROM courses
        WHERE 1=1
    """

    if crsid:
        query += f" AND 課程代碼 = '{crsid}'"
    if crsclass:
        query += f" AND 開課班別 = '{crsclass}'"
    if crslimit:
        query += f" AND 可跨班 = '{crslimit}'"
    if is_all_eng:
        query += f" AND 全英語授課 = '{is_all_eng}'"
    if is_dis_learn == "是":
        query += f" AND 備註 like '%遠距課程%'"
    if is_dis_learn == "否":
        query += f" AND 備註 not like '%遠距課程%'"

    query += f" AND 課程名稱 like '%{crsnm}%'"
    query += f" AND 教師姓名 like '%{tchnm}%'"

    cursor.execute(query)
    res = cursor.fetchall()

    select_res = gen_search_res(res)
    conn.close()
    return select_res


async def update_db_periodically():
    while True:
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] course data update start.....")
        with Timer("load_into_db"):
            await load_into_db(112, 2)

            await load_into_db(112, 1)
            # await load_into_db(111, 2)
            # await load_into_db(111, 1)
            # await load_into_db(110, 2)
            # await load_into_db(110, 1)
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] course data updated.")
        await asyncio.sleep(30)  # Update every 30 seconds


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_db_periodically())
