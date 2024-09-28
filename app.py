from flask import Flask, render_template, request , send_file, render_template_string
import os
import csv
import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select



# flaskアプリの明示
templates_path = 'templates/'
static_path = 'static/'
app = Flask(__name__ , template_folder=templates_path, static_folder=static_path)

# パスの定義
img_path_from_static = "img/"
csv_path_from_static = "media/output.csv"
csv_path = static_path + "media/output.csv"


# 環境変数の取得
user_id , password = os.environ.get('SECRET_USER_ID') , os.environ.get('SECRET_PASSWORD')



def read_html_file_to_string(html_file_path):
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_string = file.read()
    return html_string


def browser_setup(browse_visually = "no"):
    """ブラウザを起動する関数"""
    #ブラウザの設定
    options = webdriver.ChromeOptions()
    if browse_visually == "no":
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    #ブラウザの起動
    browser = webdriver.Chrome(options=options , service=ChromeService(ChromeDriverManager().install()))
    browser.implicitly_wait(3)
    return browser


def list_to_csv(to_csv_list: list , csv_path: str = "output.csv"):
    """ 多次元リストのデータをcsvファイルに保存する関数 """
    with open(csv_path, 'w' , encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(to_csv_list)


def html_table_tag_to_csv_list(table_tag_str: str, header_exist: bool = True):
    table_soup = BeautifulSoup(table_tag_str, 'html.parser')
    rows = []
    if header_exist:
        for tr in table_soup.find_all('tr'):
            cols = [] 
            for td in tr.find_all(['td', 'th']):
                cols.append(td.text.strip())
            rows.append(cols)
    else:
        for tbody in table_soup.find_all('tbody'):
            for tr in tbody.find_all('tr'):
                cols = [td.text.strip() for td in tr.find_all(['td', 'th'])]
                rows.append(cols)
    return rows


def get_building_number(page_count_info: str):
    # 正規表現を使用して物件の件数を抽出する関数
    numbers = re.findall(r'\d+', page_count_info)
    # 数字が3つ以上見つかった場合、それぞれの数字を返す
    if len(numbers) >= 3:
        start_number = int(numbers[0])
        end_number = int(numbers[1])
        total_number = int(numbers[2])
        return start_number, end_number, total_number
    else:
        return None


def scraping_reins(
        driver: WebDriverWait , 
        user_id: str , 
        password: str ,
        search_method_value: str ,
    ):
    # ドライバーの待機時間の設定
    wait_time = 5
    wait_driver = WebDriverWait(driver, wait_time)

    # ログインボタンをクリック
    login_button = wait_driver.until(EC.element_to_be_clickable((By.ID, "login-button")))
    login_button.click()

    # フォームにログイン認証情報を入力
    user_id_form = wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
    user_id_form.send_keys(user_id)
    password_form = wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
    password_form.send_keys(password)
    rule_element = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and contains(following-sibling::label, 'ガイドライン')]")))
    rule_checkbox_form = rule_element.find_element(By.XPATH, "./following-sibling::label")
    rule_checkbox_form.click()
    save_element = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and contains(following-sibling::label, '保存する')]")))
    # save_checkbox_form = save_element.find_element(By.XPATH, "./following-sibling::label")
    # save_checkbox_form.click()
    time.sleep(0.5)
    login_button = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'ログイン')]")))
    login_button.click()

    # ボタン「売買 物件検索」をクリック
    sold_building_search_button = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '売買') and contains(text(), '物件検索')]")))
    sold_building_search_button.click()

    # 売買検索条件を入力し、検索
    display_search_method_link = wait_driver.until(EC.presence_of_element_located((By.XPATH, "(//div[@class='card p-card'])[1]"))).find_element(By.XPATH, ".//a[contains(span, '検索条件を表示')]")
    display_search_method_link.click()
    choice_search_method = Select(wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='p-selectbox']//select"))))
    choice_search_method.select_by_value(search_method_value)
    get_button = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '読込')]")))
    get_button.click()
    time.sleep(0.5)
    ok_button = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'OK')]")))
    ok_button.click()
    time.sleep(0.5)
    search_button = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='p-frame-bottom']//button[contains(text(), '検索')]")))
    search_button.click()

    # 物件リストが何ページあるかを判定
    time.sleep(1)
    page_count_info = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '～') and contains(text(), '件') and contains(text(), '／')]"))).text
    start_number, end_number, total_number = get_building_number(page_count_info)
    left_page_count = total_number / 50

    # リストを取得
    loop_count = 0
    all_list = []
    while True:
        # 印刷表示ボタンをクリック
        print_button = wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '印刷')]")))
        print_button.click()
        
        # 現在のページのHTML要素を取得
        table_tag_str = wait_driver.until(EC.presence_of_element_located((By.TAG_NAME, "table"))).get_attribute('outerHTML')
        # tableタグの要素を多次元リストに変換
        if loop_count == 0:
            header_exist = True
        else:
            header_exist = False
        loop_count += 1

        to_csv_list = html_table_tag_to_csv_list(
            table_tag_str = table_tag_str , header_exist = header_exist ,
        )
        all_list.append(to_csv_list)

        if left_page_count >= 1:
            left_page_count -= 1
            # リストの表示ページへ戻る
            back_button = wait_driver.until(EC.element_to_be_clickable((By.CLASS_NAME, 'p-frame-backer')))
            back_button.click()
            # 次のリストを表示させるボタンをクリック
            next_list_button = wait_driver.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li.page-item button span.p-pagination-next-icon')))
            next_list_button.click()

        else:
            break

    driver.quit()
    

    # 全ての多次元リストを連結
    to_csv_list = []
    for loop in range( len(all_list) ):
        to_csv_list.extend( all_list[loop] )    
    
    return to_csv_list




class Reins_Scraper:
    def __init__(self, driver: WebDriverWait):
        self.driver = driver
        self.wait_driver = WebDriverWait(driver, 5)
    
    def login_reins(self, user_id: str , password: str ,):
        # ログインボタンをクリック
        login_button = self.wait_driver.until(EC.element_to_be_clickable((By.ID, "login-button")))
        login_button.click()
        time.sleep(2)

        # フォームにログイン認証情報を入力
        user_id_form = self.wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))
        user_id_form.send_keys(user_id)
        password_form = self.wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        password_form.send_keys(password)
        rule_element = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and contains(following-sibling::label, 'ガイドライン')]")))
        rule_checkbox_form = rule_element.find_element(By.XPATH, "./following-sibling::label")
        rule_checkbox_form.click()
        time.sleep(0.5)
        login_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'ログイン')]")))
        login_button.click()
        time.sleep(2)

    def get_solding_or_rental_option(self):
        # ボタン「売買 物件検索」をクリック
        sold_building_search_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '売買') and contains(text(), '物件検索')]")))
        sold_building_search_button.click()
        time.sleep(2)
        # 検索条件を取得
        display_search_method_link = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "(//div[@class='card p-card'])[1]"))).find_element(By.XPATH, ".//a[contains(span, '検索条件を表示')]")
        display_search_method_link.click()
        time.sleep(2)
        # 検索条件のリストを取得
        select_element = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='p-selectbox']//select")))
        search_method_element_list = select_element.find_elements(By.TAG_NAME, "option")
        solding_search_method_list = []
        for search_method_element in search_method_element_list:
            solding_search_method_list.append( search_method_element.text )
        # 前のページに戻る
        self.driver.back()
        time.sleep(2)

        # ボタン「売買 物件検索」をクリック
        rental_building_search_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '賃貸') and contains(text(), '物件検索')]")))
        rental_building_search_button.click()
        time.sleep(2)
        # 検索条件を取得
        display_search_method_link = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "(//div[@class='card p-card'])[1]"))).find_element(By.XPATH, ".//a[contains(span, '検索条件を表示')]")
        display_search_method_link.click()
        time.sleep(2)
        # 検索条件のリストを取得
        select_element = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='p-selectbox']//select")))
        search_method_element_list = select_element.find_elements(By.TAG_NAME, "option")
        rental_search_method_list = []
        for search_method_element in search_method_element_list:
            rental_search_method_list.append( search_method_element.text )
        # 前のページに戻る
        self.driver.back()
        time.sleep(2)
        return solding_search_method_list , rental_search_method_list
        
    def scraping_solding_list(self , search_method_value: str , index_of_search_requirement: int):
        # 選択された検索方法をクリック
        if search_method_value == "search_solding":
            building_search_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '売買') and contains(text(), '物件検索')]")))
            building_search_button.click()
        else:
            building_search_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '賃貸') and contains(text(), '物件検索')]")))
            building_search_button.click()
        time.sleep(2)

        # 売買検索条件を選択
        display_search_method_link = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "(//div[@class='card p-card'])[1]"))).find_element(By.XPATH, ".//a[contains(span, '検索条件を表示')]")
        display_search_method_link.click()
        time.sleep(2)
        choice_search_method = Select(self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='p-selectbox']//select"))))
        choice_search_method.select_by_index(index_of_search_requirement)
        get_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '読込')]")))
        get_button.click()
        time.sleep(2)

        # 検索条件が存在するか判定
        exist_search_requirement_sentence = self.wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[class*="modal"]'))).text
        if "エラー" in exist_search_requirement_sentence:
            to_csv_list = False
            self.driver.quit()
            return to_csv_list
        
        ok_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'OK')]")))
        ok_button.click()
        time.sleep(0.5)

        # 検索条件に基づいて検索実行
        search_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//div[@class='p-frame-bottom']//button[contains(text(), '検索')]")))
        search_button.click()

        # 物件リストが何ページあるかを判定
        time.sleep(2)
        page_count_info = self.wait_driver.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.card-header"))).text
        match = re.search(r'(\d+)件', page_count_info)
        total_number = int( match.group(1) )
        left_page_count = total_number / 50 

        # リストを取得
        loop_count = 0
        all_list = []
        while True:
            # 印刷表示ボタンをクリック
            print_button = self.wait_driver.until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), '印刷')]")))
            print_button.click()
            time.sleep(2)
            
            # 現在のページのHTML要素を取得
            table_tag_str = self.wait_driver.until(EC.presence_of_element_located((By.TAG_NAME, "table"))).get_attribute('outerHTML')
            # tableタグの要素を多次元リストに変換
            if loop_count == 0:
                header_exist = True
            else:
                header_exist = False
            loop_count += 1

            to_csv_list = html_table_tag_to_csv_list(
                table_tag_str = table_tag_str , header_exist = header_exist ,
            )
            all_list.append(to_csv_list)

            if left_page_count >= 1:
                left_page_count -= 1
                # リストの表示ページへ戻る
                back_button = self.wait_driver.until(EC.element_to_be_clickable((By.CLASS_NAME, 'p-frame-backer')))
                back_button.click()
                time.sleep(1)
                # 次のリストを表示させるボタンをクリック
                next_list_button = self.wait_driver.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li.page-item > button > span.p-pagination-next-icon')))
                next_list_button.click()
                time.sleep(2)

            else:
                break

        self.driver.quit()
        
        # 全ての多次元リストを連結
        to_csv_list = []
        for loop in range( len(all_list) ):
            to_csv_list.extend( all_list[loop] )    
        
        return to_csv_list






@app.route('/')
def index():
    global reins_sraper , solding_search_method_list , rental_search_method_list

    # ページにアクセス
    searched_url = "https://system.reins.jp/"
    driver = browser_setup()
    reins_sraper = Reins_Scraper(driver)
    driver.get(searched_url)

    # ログイン突破
    reins_sraper.login_reins(user_id , password)
    solding_search_method_list , rental_search_method_list = reins_sraper.get_solding_or_rental_option()

    return render_template(
        "index.html" ,
        solding_search_method_list = solding_search_method_list ,
        rental_search_method_list = rental_search_method_list ,
    )
    
    
@app.route('/result', methods=['GET', 'POST'])
def result():
    global reins_sraper , solding_search_method_list , rental_search_method_list
    if request.method == 'POST' and request.form['start_scraping'] == "true":
        # フォームから検索方法を取得
        search_method_value = request.form['search_method_value']
        # フォームから検索条件を取得
        search_requirement = request.form['solding'] if search_method_value == 'search_solding' else request.form['rental']

        if search_method_value == "search_solding":
            index_of_search_requirement = solding_search_method_list.index(search_requirement)
        else:
            index_of_search_requirement = rental_search_method_list.index(search_requirement)
        
        # リストの取得実行
        to_csv_list = reins_sraper.scraping_solding_list(search_method_value , index_of_search_requirement)
        if to_csv_list == False:
            
            return render_template(
                "result.html" ,
                search_method_value = search_method_value ,
                search_requirement = search_requirement ,
                no_exist_search_requirement = True ,
            )
        
        # リストをCSVファイルに保存
        list_to_csv(to_csv_list = to_csv_list , csv_path = csv_path ,)
        
        return render_template(
            "result.html" ,
            search_method_value = search_method_value ,
            search_requirement = search_requirement ,
            csv_path_from_static = csv_path_from_static ,
        )



@app.route('/download')
def download():
    directory = os.path.join(app.root_path, 'files') 
    return send_file(os.path.join(directory, csv_path), as_attachment=True)



if __name__ == "__main__":
    port_number = 8810
    app.run(port = port_number , debug=True)




