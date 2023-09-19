################################################################################
#
# Copyright (c) 2016 Kai Yang, Inc. All Rights Reserved
#
################################################################################
"""
This module delete repeated files and directories.

Authors: Kai Yang
Date: 2016/02/04 18:00:00
"""

import os,sys,hashlib,glob,logging.handlers,shutil,time,configparser

def get_dirname(string):
    return os.path.dirname(string)

def init_log(logfile):
    logging.basicConfig(filename=logfile,level=logging.DEBUG, encoding="utf-8")

def write_log(msg):
    timestr = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    logmsg = "%s\t%s" % (timestr , msg)
    print(logmsg)
    logging.info(logmsg)

def sumfile(fobj):    
    m = hashlib.md5()
    while True:
        d = fobj.read(8096)
        if not d:
            break
        m.update(d)
    return m.hexdigest()

#get md5sum of file
def md5sum(fname):    
    if fname == '-':
        ret = sumfile(sys.stdin)
    else:
        #try:
        f = open(fname, 'rb')
        #except:
        #write_log("FATAL: Failed to open file [%s]" % fname)
        ret = sumfile(f)+"-"+str(os.path.getsize(fname))
        f.close()
    return ret

#load garbage dict
def load_garbage_dict(dirname, garbage_dict):
    for item in os.listdir(dirname):
        subpath = os.path.join(dirname, item)
        if os.path.isdir(subpath):
            load_garbage_dict(subpath, garbage_dict)
        elif os.path.isfile(subpath):
            md5value=md5sum(subpath)
            garbage_dict[md5value]=subpath
            write_log("md5value[%s]\tfile[%s]" %(md5value, subpath))

#get md5sum of msg
def md5sum_msg(msg):
    m = hashlib.md5()
    m.update(msg.encode())
    return m.hexdigest()

#get md5sum for dir message(files' name and length, exclude html and txt)
def gen_dir_md5sum(dirname):
    dir_msg=""
    for item in os.listdir(dirname):
        subpath = os.path.join(dirname, item)
        if os.path.isfile(subpath):
            subfix = os.path.splitext(subpath)[1][1:].lower()
            if subfix == "html" or subfix=="txt" or subfix=="db" or subfix=="torrent":
                continue
            dir_msg+=("%s\t%d\t" % (item, os.path.getsize(subpath)))
    return md5sum_msg(dir_msg)

#build the digest for dir
def build_dir_msg(dirname, subpath, dirsum):
    fp=open(subpath, "w", encoding="utf-8")
    fp.write("%s\n" % dirsum)
    for item in os.listdir(dirname):
        subpath = os.path.join(dirname, item)
        if os.path.isfile(subpath):
            subfix = os.path.splitext(subpath)[1][1:].lower()
            if subfix == "html" or subfix=="txt" or subfix=="db" or subfix=="torrent":
                continue
            md5value=md5sum(subpath)
            #print(subpath)
            fp.write("%s\t%s\n" % (item, md5value))
    fp.write("END\n")
    fp.close()

#check if digest for dir changes, include files'name file's length
def if_dir_change(subpath, dirsum):
    fp=open(subpath, "r", encoding="utf-8")
    line_list=fp.readlines()
    fp.close()
    line_num=len(line_list)
    if line_num < 2:
        write_log("FATAL\tdirsum file[%s] format error" % subpath)
        return True
    if line_num > 0:
        if line_list[0].replace("\n","") != dirsum:
            write_log("dirsum file[%s] changed, rebuild it" % subpath)
            return True
        elif line_list[line_num-1].replace("\n","") != "END":
            write_log("dirsum file[%s] no END, rebuild it" % subpath)
            return True
    else:
        write_log("dirsum file[%s] no line, rebuild it" % subpath)
        return True

#read the digest file for dir to append to file list
def read_filelist(subpath, filelist):
    dirname=get_dirname(subpath)
    fp=open(subpath, "r", encoding="utf-8")
    line_list=fp.readlines()
    fp.close()
    line_num=len(line_list)
    if line_num < 2:
        write_log("FATAL\tdirsum file[%s] format error" % subpath)
        return
    for i in range(1,line_num-1):
        line_array=line_list[i].replace("\n","").split("\t")
        if len(line_array) !=2:
            write_log("FATAL\tdirsum file[%s] line%d[%s] format error" % (subpath, i, line_list[i]))
            continue
        fname=os.path.join(dirname, line_array[0])
        md5value=line_array[1]
        filelist.append([fname, md5value])

#calculate the total valid file(exclude en and txt) number
def total_dir(dirname):
    number=0
    for item in os.listdir(dirname):
        subpath = os.path.join(dirname, item)
        try:
            if os.path.isdir(subpath):
                number+=total_dir(subpath)
            elif os.path.isfile(subpath):
                subfix = os.path.splitext(subpath)[1][1:].lower()
                
                if subfix == "html" or subfix=="txt" or subfix=="db" or subfix=="torrent":
                    continue
                number+=1
        except Exception as ex:
            continue
    return number

#check dir recursive
def check_dir(dirname, filelist,totalnum):
    if_has_son_dir=False
    #print(dirname)
    #try:
    if True:
        for item in os.listdir(dirname):
            subpath = os.path.join(dirname, item)
            #print(subpath)
            if os.path.isdir(subpath):
                if_has_son_dir=True
                #print(if_has_son_dir)
                check_dir(subpath, filelist, totalnum)
        #print(if_has_son_dir)
        #if not if_has_son_dir:
        if True:
            dirsum=gen_dir_md5sum(dirname)
            subpath = os.path.join(dirname, "dirsum.txt")
            print(subpath)
            if not os.path.exists(subpath):
                print(subpath)
                write_log("dirsum file[%s] not exist, create it" % subpath)
                build_dir_msg(dirname, subpath, dirsum)
            elif if_dir_change(subpath, dirsum):            
                build_dir_msg(dirname, subpath, dirsum)
            read_filelist(subpath, filelist)
            write_log("total: %d\tcurrent: %d" % (totalnum, len(filelist)))
    #except Exception as ex:
    #    pass
    #print(dirname)

#mv file to dst dir
def mv_file(src_dir, dst_dir, oldpic, similarpic):
    newpic = dst_dir+oldpic[len(src_dir):]
    if not os.path.exists(oldpic):
        write_log("FATAL: file [%s] not exist!" % oldpic)
        return
    newdir=get_dirname(newpic)
    try:
        if not os.path.exists(newdir):
            os.makedirs(newdir)
    except Exception as ex:
        pass
    try:
        shutil.move(oldpic, newpic)
    except Exception as ex:
        pass
    write_log("move\n%s\nto\n%s\nsimilar to\n%s\n######################################" % (oldpic, newpic, similarpic))

def del_repeat_and_garbage(root_dir, file_list, garbage_dict, garbage_dir, repeatfile_dir, dir_dict):
    #record the change directory, for recreate dirsum for these directorys
    change_dir_dict={}
    total_file_num=len(file_list)
    for i in range(total_file_num):
        if i % 10000 == 0:
            write_log("del_repeat_and_garbage total: %d\tcurrent: %d" %(total_file_num, i))
        #file name
        fname=file_list[i][0]
        #directory name
        dname=get_dirname(fname)
        #if dirname not in dir dict, then build a file dict insert into dir_dict
        if dname not in dir_dict:
            file_dict={}
            dir_dict[dname]=file_dict
        #file md5 value
        md5value=file_list[i][1]
        #if file is a garbage
        if md5value in garbage_dict:
            change_dir_dict[dname]=0
            mv_file(root_dir, garbage_dir, fname, garbage_dict[md5value])
        #if file in file dict
        elif md5value in dir_dict[dname]:
            change_dir_dict[dname]=0
            mv_file(root_dir, repeatfile_dir, fname, dir_dict[dname][md5value])
        #insert into dir dict
        else:
            dir_dict[dname][md5value]=fname
    #walk on all the change directorys, to recreate dirsum
    total_dir_num=len(change_dir_dict)
    x=0
    for dirname in change_dir_dict:
        if x % 10 == 0:
            write_log("rebuild_dirsum total: %d\tcurrent: %d" %(total_dir_num, x))
        x+=1
        dirsum=gen_dir_md5sum(dirname)
        subpath = os.path.join(dirname, "dirsum.txt")
        if not os.path.exists(subpath):
            write_log("dirsum file[%s] not exist, create it" % subpath)
            build_dir_msg(dirname, subpath, dirsum)
        elif if_dir_change(subpath, dirsum):
            build_dir_msg(dirname, subpath, dirsum)

#output the filelist and md5values to result file
def output_dir2(dir_dict, result_file):
    fi= open(result_file, "w", encoding="utf-8")
    for d in dir_dict:
        for md5value in dir_dict[d]:
            fi.write("%s\t%s\n" % (dir_dict[d][md5value], md5value))
    fi.close()

def get_md5value():
    g_garbage_dict={}
    g_file_list=[]
    g_dir_dict={}
    cf = configparser.ConfigParser()
    cf.read("config.conf")
    g_log_file=cf.get("del_reapeat", "LOG_FILE")
    init_log(g_log_file)
    write_log("PROGRAM BEGIN")
    g_garbage_dir=cf.get("del_reapeat","GARBAGE_FILES_DIR")
    g_target_dir=cf.get("global", "TARGET_DIR")
    g_result_file=cf.get("del_reapeat", "MD5VALUE_RESULT")
    timestr = time.strftime('%Y%m%d-%H%M',time.localtime(time.time()))
    g_garbage_res_dir=os.path.join(get_dirname(g_target_dir), "garbagefile_%s\\" % timestr)
    g_repeatfile_res_dir=os.path.join(get_dirname(g_target_dir), "repeatfile_%s\\" % timestr)
    g_target_dir+="\\"
    g_target_dir = g_target_dir
    g_garbage_dir = g_garbage_dir
    g_garbage_res_dir = (g_garbage_res_dir)
    g_repeatfile_res_dir = (g_repeatfile_res_dir)
    g_result_file = (g_result_file)
    write_log("garbage dir: %s" % g_garbage_dir)
    write_log("target dir: %s" % g_target_dir)
    write_log("md5value result file: %s" % g_result_file)
    write_log("load_garbage_dict...")
    load_garbage_dict(g_garbage_dir, g_garbage_dict)
    write_log("load_garbage_dict end")
    write_log("total garbage files: %d" % len(g_garbage_dict))
    write_log("total_dir...")
    #x = raw_input("total picture number:\n")
    #if x=="":
    #    g_totalnum=total_dir(g_target_dir)
    #else:
    #    g_totalnum=int(x)
    g_totalnum=total_dir(g_target_dir)
    write_log("total_dir end")
    write_log("total_number:%d" % g_totalnum)
    write_log("check_dir...")
    check_dir(g_target_dir, g_file_list, g_totalnum)
    write_log("check_dir end")
    write_log("del_repeat_and_garbage...")
    del_repeat_and_garbage(g_target_dir, g_file_list, g_garbage_dict, g_garbage_res_dir, g_repeatfile_res_dir, g_dir_dict)
    write_log("del_repeat_and_garbage end")
    write_log("output_dir...")
    output_dir2(g_dir_dict, g_result_file)
    write_log("output_dir end")
    write_log("PROGRAM END")

def load_md5value_file(input_file, dir_dict, pic_dict):
    fp=open(input_file, "r", encoding="utf-8")
    picno=0
    for line in fp.readlines():
        line_array=line.split("\t")
        filename=line_array[0]
        md5value=line_array[1].replace("\n","")
        dirname=get_dirname(filename)
        #print filename
        #print md5value
        #print dirname
        if (dirname not in dir_dict):
            #if not os.path.isdir(dirname):
            #    write_log("FATAL\tfile[%s]'s path[%s] is not a directory" % (filename, dirname))
            #    continue
            subdir_dict={}
            subdir_dict[filename]=md5value
            dir_dict[dirname]=subdir_dict
        else:
            dir_dict[dirname][filename]=md5value

        if (md5value not in pic_dict):
            dirs_dict={}
            dirs_dict[dirname]= 1
            pic_dict[md5value]=dirs_dict
        else:
            pic_dict[md5value][dirname]=1
        picno+=1
    write_log("total input pictures: %d" % picno)

def get_father(dir_dict, pic_dict, father_dict, target_dir):
    for d in dir_dict:
        if target_dir != d[:len(target_dir)]:
            continue
        temp_dict={}
        #walk on all the files of folder d to build the dict for the union of all the files' folders
        for f in dir_dict[d]:
            for x in pic_dict[dir_dict[d][f]]:
                if x not in temp_dict:
                    temp_dict[x] = 1
                else:
                    temp_dict[x]= temp_dict[x] + 1
        #walk on temp_dict to build son and father relation
        for item in temp_dict:
            i = item
            #get d's father and make ture d's father is not itself
            if (temp_dict[i] == len(dir_dict[d])) and (d != i):
                #if i's father already is d, then don't mark d's father be i
                if (i in father_dict) and (father_dict[i] == d):
                    write_log("brothers\t%s\t%s" % (d, i))
                    continue
                write_log("get_father\t%s\t%s" % (d, i))
                #if i has father and not be d, then mark i be i's father
                if (i in father_dict):
                    write_log("rep_grandpa\t%s\t%s" % (i, father_dict[i]))
                    i=father_dict[i]
                #replace the father of d's son
                for y in father_dict:
                    if father_dict[y] == d:
                        father_dict[y]=i
                        write_log("rep_father\t%s\tfather\tfrom\t%s\tto\t%s" % (y, d, i))
                #replace the father of d
                father_dict[d]=i
                break
        temp_dict.clear()

def output_relation(father_dict, output_file):
    fi= open(output_file, "w", encoding="utf-8")
    for d in father_dict:
        fi.write("%s\t%s\n" % (d, father_dict[d]))
    fi.close()

#output the filelist and md5values to result file
def output_dir3(dir_dict, father_dict, result_file):
    fi= open(result_file, "w", encoding="utf-8")
    picno=0
    for d in dir_dict:
        if d not in father_dict:
            for f in dir_dict[d]:
                picno+=1
                fi.write("%s\t%s\n" % (f, dir_dict[d][f]))
    fi.close()
    write_log("total output pictures: %d" % picno)

def get_father_relation():
    g_dir_dict={}
    g_pic_dict={}
    g_father_dict={}
    cf = configparser.ConfigParser()
    cf.read("config.conf")
    g_log_file=cf.get("del_reapeat", "LOG_FILE")
    init_log(g_log_file)
    write_log("PROGRAM BEGIN")
    g_target_dir=cf.get("global", "TARGET_DIR")
    g_input_file_base=cf.get("del_reapeat", "BASE_MD5VALUE_RESULT")
    g_input_file=cf.get("del_reapeat", "MD5VALUE_RESULT")
    g_output_file=cf.get("del_reapeat", "FATHER_RELATION")
    g_target_dir+="\\"
    g_target_dir = (g_target_dir)
    g_input_file = (g_input_file)
    g_output_file = (g_output_file)
    write_log("md5value result: %s" % g_input_file)
    write_log("father relation: %s" % g_output_file)
    write_log("load_md5value_file...")
    load_md5value_file(g_input_file, g_dir_dict, g_pic_dict)
    write_log("load_md5value_file end")
    if os.path.exists(g_input_file_base):
        write_log("load_md5value_base_file...")
        load_md5value_file(g_input_file_base, g_dir_dict, g_pic_dict)
        write_log("load_md5value_base_file end")
    write_log("get_father...")
    get_father(g_dir_dict, g_pic_dict, g_father_dict, g_target_dir)
    write_log("get_father end")
    write_log("output_relation...")
    output_relation(g_father_dict, g_output_file)
    write_log("output_relation end")
    write_log("output_dir...")
    output_dir3(g_dir_dict, g_father_dict, g_input_file+"_new.txt")
    write_log("output_dir end")
    write_log("PROGRAM END")

def disposal_file(input_file, father_dict):
    fp=open(input_file, "r", encoding="utf-8")
    for line in fp.readlines():
        line_array=line.split("\t")
        sonname=line_array[0]
        fathername=line_array[1].replace("\n","")
        father_dict[sonname]=fathername

def mv_dir(src_dir, dst_dir, father_dict):
    for olddir in father_dict:
        has_son_dir = False
        for item in os.listdir(olddir):
            subpath = os.path.join(olddir, item)
            if os.path.isdir(subpath):
                has_son_dir = True
                break
        #if has_son_dir:
        #    continue
        newdir = dst_dir+olddir[len(src_dir):]
        if not os.path.exists(newdir):
            #write_log("makedir[%s]" % newdir)
            try:
                os.makedirs(newdir)
            except Exception as ex:
                pass
        for item in os.listdir(olddir):
            oldpath=os.path.join(olddir,item)
            if os.path.isdir(oldpath):
                continue
            newpath=os.path.join(newdir,item)
            #write_log("src[%s] dst[%s]" % (oldpath, newpath))
            try:
                shutil.move(oldpath, newpath)
            except Exception as ex:
                pass
        if not has_son_dir and len(os.listdir(olddir))==0:
            os.rmdir(olddir)
        write_log("final_father src\n%s\n new\n%s\n father\n%s\n######################################" % (olddir, newdir, father_dict[olddir]))

def mv_repeat():
    g_father_dict={}
    cf = configparser.ConfigParser()
    cf.read("config.conf")
    g_log_file=cf.get("del_reapeat", "LOG_FILE")
    init_log(g_log_file)
    write_log("PROGRAM BEGIN")
    g_target_dir=cf.get("global", "TARGET_DIR")
    g_input_file=cf.get("del_reapeat", "FATHER_RELATION")
    timestr = time.strftime('%Y%m%d-%H%M',time.localtime(time.time()))
    g_result_dir=os.path.join(os.path.dirname(g_target_dir), "repeatdir_%s\\" % timestr)
    g_target_dir+="\\"
    g_target_dir = (g_target_dir)
    g_result_dir = (g_result_dir)
    g_input_file = (g_input_file)
    write_log("father relation file: %s" % g_input_file)
    write_log("target dir: %s" % g_target_dir)
    write_log("result dir: %s" % g_result_dir)
    write_log("disposal_file...")
    disposal_file(g_input_file, g_father_dict)
    write_log("disposal_file end")
    write_log("mv_dir...")
    mv_dir(g_target_dir, g_result_dir, g_father_dict)
    write_log("mv dir end")
    write_log("PROGRAM END")

get_md5value()
get_father_relation()
mv_repeat()
