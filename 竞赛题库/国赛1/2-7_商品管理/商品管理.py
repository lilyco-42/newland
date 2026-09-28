# -*- coding: utf-8 -*-
"""套1 2-7 商品管理系统 - Python 3.6 兼容"""
import os
import json
import time

try:
    import requests
except ImportError:
    requests = None

DB_FILE = "products.json"


class NLECloudClient:
    """新大陆物联网云平台 API 客户端"""
    BASE = "http://api.nlecloud.com"

    def __init__(self):
        self.token = ""

    def login(self, account, password):
        r = requests.post(
            "%s/Users/Login" % self.BASE,
            json={"Account": account, "Password": password, "IsRememberMe": True},
        )
        data = r.json()
        if data["Status"] == 0:
            self.token = data["ResultObj"]["AccessToken"]
            return True
        return False

    def upload_data(self, device_id, api_tag, value):
        r = requests.post(
            "%s/Devices/%s/Datas" % (self.BASE, device_id),
            headers={"AccessToken": self.token},
            json={"DatasDTO": [{"ApiTag": api_tag, "Value": str(value)}]},
        )
        return r.json()


class ProductDB:
    """本地JSON数据库"""
    def __init__(self, path=DB_FILE):
        self.path = path
        self.products = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.products = json.load(f)
        else:
            self.products = []

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)

    def add(self, name, price, stock, category="默认"):
        pid = int(time.time() * 1000) % 1000000
        product = {
            "id": pid,
            "name": name,
            "price": float(price),
            "stock": int(stock),
            "category": category,
        }
        self.products.append(product)
        self.save()
        return product

    def delete(self, pid):
        self.products = [p for p in self.products if p["id"] != pid]
        self.save()

    def update(self, pid, **kw):
        for p in self.products:
            if p["id"] == pid:
                p.update(kw)
                self.save()
                return p
        return None

    def search(self, keyword=""):
        if not keyword:
            return self.products
        kw = keyword.lower()
        return [p for p in self.products if kw in p["name"].lower()
                or kw in p["category"].lower()]

    def get_by_category(self, category):
        if not category or category == "全部":
            return self.products
        return [p for p in self.products if p["category"] == category]

    def get_categories(self):
        cats = set()
        for p in self.products:
            cats.add(p["category"])
        return sorted(cats)

    def total_value(self):
        return sum(p["price"] * p["stock"] for p in self.products)


class ProductManager:
    """商品管理系统"""
    def __init__(self):
        self.db = ProductDB()
        self.cloud = None

    def connect_cloud(self, account, password):
        if requests:
            self.cloud = NLECloudClient()
            if self.cloud.login(account, password):
                print("[OK] 云平台已连接")
                return True
        return False

    def sync_to_cloud(self, device_id=1):
        """同步库存数据到云平台"""
        if not self.cloud:
            return
        total = len(self.db.products)
        value = self.db.total_value()
        self.cloud.upload_data(device_id, "product_count", total)
        self.cloud.upload_data(device_id, "total_value", value)
        print("[SYNC] 商品数=%d  总价值=%.2f" % (total, value))

    def print_list(self, products=None):
        """打印商品列表"""
        if products is None:
            products = self.db.products
        print("\n%-8s %-16s %8s %6s %s" % ("ID", "名称", "价格", "库存", "分类"))
        print("-" * 55)
        for p in products:
            print("%-8d %-16s %8.2f %6d %s" % (
                p["id"], p["name"], p["price"], p["stock"], p["category"],
            ))
        print("-" * 55)
        print("共 %d 件商品  总价值: %.2f" % (len(products), self.db.total_value()))

    def interactive(self):
        """交互式菜单"""
        print("=" * 40)
        print("  商品管理系统")
        print("=" * 40)
        while True:
            print("\n1.添加  2.删除  3.修改  4.查询")
            print("5.分类  6.列表  7.同步云  0.退出")
            choice = input("请选择: ").strip()
            if choice == "1":
                name = input("名称: ").strip()
                price = float(input("价格: ").strip())
                stock = int(input("库存: ").strip())
                cat = input("分类(默认): ").strip() or "默认"
                p = self.db.add(name, price, stock, cat)
                print("[OK] 已添加: %s" % p["name"])
            elif choice == "2":
                pid = int(input("商品ID: ").strip())
                self.db.delete(pid)
                print("[OK] 已删除")
            elif choice == "3":
                pid = int(input("商品ID: ").strip())
                name = input("新名称(回车跳过): ").strip()
                price = input("新价格(回车跳过): ").strip()
                stock = input("新库存(回车跳过): ").strip()
                kw = {}
                if name:
                    kw["name"] = name
                if price:
                    kw["price"] = float(price)
                if stock:
                    kw["stock"] = int(stock)
                self.db.update(pid, **kw)
                print("[OK] 已更新")
            elif choice == "4":
                kw = input("搜索关键词: ").strip()
                results = self.db.search(kw)
                self.print_list(results)
            elif choice == "5":
                cats = ["全部"] + self.db.get_categories()
                for i, c in enumerate(cats):
                    print("  %d.%s" % (i, c))
                idx = int(input("选择分类: ").strip())
                cat = cats[idx]
                self.print_list(self.db.get_by_category(cat))
            elif choice == "6":
                self.print_list()
            elif choice == "7":
                self.sync_to_cloud()
            elif choice == "0":
                break


if __name__ == "__main__":
    mgr = ProductManager()
    mgr.connect_cloud("13329262958", "qwe123456789")
    mgr.interactive()
