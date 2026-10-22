"""把样片渲染成 MP4。

流程：
  1. Windows SAPI 为每个语气段合成中文配音，并测出真实时长
  2. 用真实语音时长反推时间轴（字幕与画面切换的时间点）
  3. 把时间轴注入页面，Playwright 驱动本机 Edge 无头录制画面
  4. ffmpeg 把配音轨与画面合成，输出成片 MP4

用法：  python build_video.py
"""
import json
import os
import re
import subprocess
import sys
import wave

import imageio_ffmpeg

ROOT = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(ROOT, "build")
OUT_MP4 = os.path.join(ROOT, "苏轼-样片.mp4")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SAPI_RATE = 1           # -10..10；实测 -2 会慢到约 2.4 字/秒，整片拖成 2 分钟
SR = 24000

# 与页面里的 PARAS 保持一致
PARAS = [
    {"scene": 0, "pause": 200, "sents": [
        "你有没有过这样一天。",
        "你说的一句话，被人截出来传。传到最后，变成了另一个意思。",
        "所有人都在议论你。没人问你，到底说了什么。"]},
    {"scene": 0, "pause": 1750, "sents": [
        "公元一〇七九年，有个人遇到了一模一样的事。",
        "他比你还惨。"]},
    {"scene": 1, "pause": 200, "sents": [
        "他叫苏轼，四十四岁，当时已经是全国最有名的文人。",
        "七月，他被抓进御史台的监狱，罪名是——写诗讥讽朝政。"]},
    {"scene": 1, "pause": 1050, "sents": [
        "在那个叫乌台的地方，他关了一百三十天。",
        "那一年，京城里有不少人觉得，他活不下来。"]},
    {"scene": 2, "pause": 200, "sents": [
        "宋人笔记里记了一件事。",
        "他在狱中和儿子约好：每天送饭，只送肉和菜。如果有一天送来的鱼，就是死讯到了。"]},
    {"scene": 2, "pause": 1700, "sents": [
        "有一天，送饭的人弄错了，真的送了一条鱼。"]},
    {"scene": 2, "pause": 700, "sents": [
        "他以为自己要死了。于是给弟弟苏辙写了两首诗：",
        "与君世世为兄弟，更结来生未了因。"]},
    {"scene": 3, "pause": 1400, "sents": [
        "后来他没死。他被贬去黄州，一个很远的小地方。",
        "四十四岁，从京城名人，变成戴罪之身。"]},
    {"scene": 4, "pause": 420, "sents": [
        "这是他人生第一次，真正的归零。"]},
]
POEM_INDEX = {(6, 1)}

os.makedirs(TMP, exist_ok=True)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.decode("utf-8", "replace")[-2000:])
        raise SystemExit("命令失败：%s" % " ".join(cmd[:5]))
    return r


def duration(path):
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True)
    txt = r.stderr.decode("utf-8", "replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", txt)
    if not m:
        raise SystemExit("读不出时长：" + path)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def to_wav(src, dst):
    run([FFMPEG, "-y", "-i", src, "-ar", str(SR), "-ac", "1", dst])


def make_silence(path, seconds):
    n = max(0, int(seconds * SR))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"\x00\x00" * n)


def sapi_synth(texts):
    """用 Windows SAPI 逐段合成中文语音。返回 wav 路径列表。"""
    import pythoncom
    pythoncom.CoInitialize()
    import win32com.client as wc

    v = wc.Dispatch("SAPI.SpVoice")
    vs = v.GetVoices()
    picked = None
    for i in range(vs.Count):
        d = vs.Item(i).GetDescription()
        if "Chinese" in d:
            v.Voice = vs.Item(i)
            picked = d
            break
    if not picked:
        raise SystemExit("系统里没有中文 SAPI 语音")
    print("  使用语音：%s" % picked)
    v.Rate = SAPI_RATE

    paths = []
    for i, text in enumerate(texts):
        raw = os.path.join(TMP, "raw%02d.wav" % i)
        stream = wc.Dispatch("SAPI.SpFileStream")
        stream.Open(raw, 3, False)
        v.AudioOutputStream = stream
        v.Speak(text)
        stream.Close()
        dst = os.path.join(TMP, "seg%02d.wav" % i)
        to_wav(raw, dst)
        paths.append(dst)
    return paths


def main():
    print("1/5  合成配音（Windows SAPI）…")
    texts = ["".join(p["sents"]) for p in PARAS]
    segs = sapi_synth(texts)
    durs = [duration(p) for p in segs]
    print("  各段时长：" + " ".join("%.1fs" % d for d in durs))

    print("2/5  按真实语音时长推算时间轴…")
    timeline = []
    t = 0.0
    for i, P in enumerate(PARAS):
        d = durs[i]
        weights = []
        for k, s in enumerate(P["sents"]):
            w = len(s)
            if (i, k) in POEM_INDEX:
                w *= 1.25
            weights.append(w)
        tot = sum(weights)
        acc = 0.0
        for k, s in enumerate(P["sents"]):
            timeline.append({
                "t": round(t + acc, 3),
                "scene": P["scene"],
                "s": s,
                "poem": 1 if (i, k) in POEM_INDEX else 0,
            })
            acc += d * weights[k] / tot
        t += d + P["pause"] / 1000.0
    total = t
    print("  总时长 %.1f 秒" % total)

    print("3/5  拼接配音轨（含段间停顿）…")
    lines = []
    for i in range(len(PARAS)):
        lines.append("file '%s'" % segs[i].replace("\\", "/"))
        sil = os.path.join(TMP, "sil%02d.wav" % i)
        make_silence(sil, PARAS[i]["pause"] / 1000.0)
        lines.append("file '%s'" % sil.replace("\\", "/"))
    concat = os.path.join(TMP, "concat.txt")
    open(concat, "w", encoding="utf-8").write("\n".join(lines))
    narration = os.path.join(TMP, "narration.wav")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat,
         "-ar", str(SR), "-ac", "1", narration])
    print("  配音轨 %.1f 秒" % duration(narration))

    print("4/5  注入时间轴并录制画面…")
    src = open(os.path.join(ROOT, "苏轼-样片.html"), encoding="utf-8").read()
    js = "const TIMELINE = " + json.dumps(timeline, ensure_ascii=False) + ";"
    if "const TIMELINE = [];" not in src:
        raise SystemExit("页面里找不到 TIMELINE 占位行")
    render = os.path.join(TMP, "render.html")
    open(render, "w", encoding="utf-8").write(src.replace("const TIMELINE = [];", js))

    from playwright.sync_api import sync_playwright
    url = "file:///" + render.replace("\\", "/") + "?auto=1&clean=1"
    launch_args = {"executable_path": EDGE} if os.path.exists(EDGE) else {}
    with sync_playwright() as p:
        b = p.chromium.launch(**launch_args)
        ctx = b.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=os.path.join(TMP, "vid"),
            record_video_size={"width": 1920, "height": 1080},
        )
        pg = ctx.new_page()
        pg.goto(url)
        pg.wait_for_timeout(int((total + 5) * 1000))
        ctx.close()
        b.close()

    vid_dir = os.path.join(TMP, "vid")
    vids = [f for f in os.listdir(vid_dir) if f.endswith(".webm")]
    if not vids:
        raise SystemExit("没有录到视频")
    vpath = os.path.join(vid_dir, sorted(vids)[-1])
    print("  录得画面 %s（%.1f 秒）" % (os.path.basename(vpath), duration(vpath)))

    print("5/5  合成成片…")
    run([FFMPEG, "-y", "-i", vpath, "-i", narration,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-shortest", OUT_MP4])
    print("完成：%s（%.1f 秒）" % (OUT_MP4, duration(OUT_MP4)))


if __name__ == "__main__":
    main()
