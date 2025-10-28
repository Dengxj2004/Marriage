from bs4 import BeautifulSoup
import os
import csv

f = open('test_file.csv', 'a+')
writer = csv.writer(f)
writer.writerow(['port_name','id','s_name','first_date','o_name','last_modified_date'])
path = r'F:\ORCID\ORCID_2021_10_summaries.tar_3\ORCID_2021_10_summaries'
portfolio = os.listdir(path) #001 002
for port_name in portfolio:
    flag = 0
    print(port_name)
    for i in os.listdir(path+'\\'+port_name): #读取每个文件夹F:\ORCID\ORCID_2021_10_summaries.tar_3\ORCID_2021_10_summaries\\001
        file = open(path+'\\'+port_name+'\\'+i,'r',encoding='utf-8')#打开每个文件 ……\\001\0000-4545-……
        soup = BeautifulSoup(file)
        try:
            first_date = soup.find("person:name").find("common:last-modified-date").string
            given_name = soup.find("person:name").find("personal-details:given-names").string
            #print(given_name)
            family_name = soup.find("person:name").find("personal-details:family-name").string
            #print(family_name)
            othername = soup.find("other-name:other-name")
            sourcename = othername.find("common:source-name").string
            othername_content = othername.find("other-name:content").string
            last_modified_date = othername.find("common:last-modified-date").string
            if sourcename != None and othername_content !=None:
                if str(family_name).lower() in str(othername_content).lower() or str(given_name).lower() in str(othername_content).lower():
                    #改连接符 不完全一致
                    s_name = str(sourcename).strip().lower().replace('-',' ').replace('.','')
                    o_name = str(othername_content).strip().lower().replace('-',' ').replace('.','')
                    if s_name.replace(' ','') != o_name.replace(' ','') and s_name.split(' ')[0] == o_name.split(' ')[0] and first_date[0:10] != last_modified_date[0:10]: #158
                        #保留两种情况 改姓 或者加了中间姓，且修改发生时间在后
                        #加中间名的不算 加姓（即女性将娘家的姓作为中间名）或者改姓的才算
                        #改姓也有可能改的姓长度不一致 通过姓有无交集确定是改姓还是加中间名
                        #娘家姓作为中间名
                        if len(list(set(s_name.split(' ')[1:]) & set(o_name.split(' ')[1:]))) > 0:
                            if len(s_name) > len(o_name) and first_date[0:10] > last_modified_date[0:10]\
                                or len(o_name) > len(s_name) and last_modified_date[0:10] > first_date[0:10]:
                                    print(s_name,'/',o_name)
                                    if s_name.split(' ') == o_name.split(' ')[0:-1] or o_name.split(' ') == s_name.split(' ')[0:-1]:
                                        flag += 1
                                        row = [port_name,soup.find("common:path").string,s_name,first_date,o_name,last_modified_date]
                                        writer.writerow(row)
                                        print(soup.find("common:path").string)
                                        print(s_name)
                                        print(first_date)
                                        print(o_name)
                                        print(last_modified_date)
                        #改姓
                        else:
                            #排除缩写情况
                            name1 = s_name.split(' ')
                            name2 = o_name.split(' ')
                            if len(name1) == 2 and (len(name1[1]) == 1 or len(name2[1]) == 1) and name1[1][0] == name2[1][0]:
                                print('abrrev')
                            else:
                                flag += 1
                                row = [port_name,soup.find("common:path").string, s_name, first_date, o_name, last_modified_date]
                                writer.writerow(row)
                                print(soup.find("common:path").string)
                                print(s_name)
                                print(first_date)
                                print(o_name)
                                print(last_modified_date)
        except:
            continue
    print(flag)

#中间的缩写是教名需要去掉 字母转换问题
