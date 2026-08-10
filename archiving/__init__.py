import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

import arxiv

from helpers import db_manager

PaperSource = ["arxiv.org", "thecvf.com", "dl.acm.org", "proceedings.mlr.press"] # "www.nature.com", "nips.cc", "neurips.cc"

# github.com/{여기}/... 가 사용자·조직이 아닌 GitHub 자체 경로인 경우
GITHUB_RESERVED_PATHS = {
    "features", "settings", "orgs", "topics", "collections", "sponsors",
    "marketplace", "explore", "notifications", "pulls", "issues", "search",
    "login", "join", "about", "pricing", "enterprise", "apps",
}

def chat2log(message):
    # DMChannel 에는 name 속성이 없다. 방어하지 않으면 DM 메시지마다
    # on_message 가 죽어 DM 커맨드가 전부 동작하지 않는다.
    log = {
            "channel_name": getattr(message.channel, "name", "DM"),
            "channel_id": str(message.channel.id),
            "message_author": message.author.display_name,
            "message_author_id": str(message.author.id),
            "message_content": message.content
        }
    return log

def get_url(message: str) -> str | None:

    """Get URL within text

    Args:
        message (str): Message content

    Returns:
        str | None: 찾은 URL. 본문에 URL 형태가 없으면 None.
    """

    # URL 정규표현식
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

    matches = re.findall(regex, message)
    if not matches:
        # "arxiv.org 좋더라" 처럼 도메인만 언급한 경우. 호출부가 조기 반환한다.
        return None
    url = matches[0][0]

    break_point = False
    for i, t in enumerate(url):
        # print(t.isascii(), end=" ")
        if not t.isascii(): 
            break_point = True
            break
    if break_point:
        url = url[:i]
    return url

def extract_github_desctiption(url: str) -> str:
    """Extract github repository description

    Args:
        url (str): page URL

    Returns:
        str: Repository descriptioin
    """
        
    
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")
    content = soup.find("p", "f4 my-3")
    return content.text.strip() if content else "No description or website provided"

async def archive_github(message):
    """저장소를 아카이브한다.

    :return: dict | None — 아카이빙 대상이 아니면 None.
             {"kind","added","original","title","url"} 형태로 호출부가
             리액션이나 중복 안내를 붙일 수 있게 결과를 돌려준다.
    """
    # Preprocessing
    url = get_url(message.content)
    if url is None:
        return None

    # owner/repo 형태를 직접 뽑는다. split("/")[-2:] 로 자르면
    # "https://github.com/" 같은 링크에서 ("https:", "github.com") 이 나온다.
    match = re.search(r"github\.com/([\w.\-]+)/([\w.\-]+)", url)
    if match is None:
        return None
    username, repo_name = match.group(1), match.group(2).removesuffix(".git")
    if username.lower() in GITHUB_RESERVED_PATHS:
        return None

    description = extract_github_desctiption(url)

    log = chat2log(message)
    log.pop("message_content")
    log.update({
        "github_username": username,
        "repository_name": repo_name,
        "description": description
        })
    added, original = await db_manager.add_github(**log)
    return {
        "kind": "github",
        "added": added,
        "original": original,
        "title": f"{username}/{repo_name}",
        "url": url,
    }

async def archive_paper(message):
    
        # Arxiv: Title, Authors, Categories, Submitted date
        # CVF: Title, Authors, Booktitle , Year
        # ACM: Title, Authors, Booktitme, Year
        # PMLR: Title, Authors, Booktitme, Year
        # NeurIPS: Title, Authors
        url = get_url(message.content)
        if url is None:
            return
        log = chat2log(message)
        log.pop("message_content")
        # print(url)
        
        if "arxiv" in url.lower():
            # ex)
            # https://arxiv.org/abs/2112.09686
            # https://arxiv.org/pdf/2112.09686.pdf
            paper_id = url.split("/")[-1].replace(".pdf", "")
            # Search.results() 는 폐기 대상이고, 결과가 없으면 StopIteration 이
            # 코루틴 안에서 RuntimeError 로 바뀐다. Client 로 받아 리스트로 확인한다.
            found = list(arxiv.Client(page_size=1, num_retries=2).results(
                arxiv.Search(id_list=[paper_id])
            ))
            if not found:
                return None
            paper = found[0]
            result_dict = {
                "source": "arxiv",
                "title": paper.title,
                "authors": "\t".join(author.name for author in paper.authors),
                "url": f"https://arxiv.org/abs/{paper_id}",
                "conference": "",
                "year": paper.published.strftime("%Y"),
                "abstract": (paper.summary or "").replace("\n", " ").strip(),
            }

        elif "thecvf" in url.lower():
            # ex)
            # https://openaccess.thecvf.com/content/ICCV2021/html/Kim_Continual_Learning_on_Noisy_Data_Streams_via_Self-Purified_Replay_ICCV_2021_paper.html
            # https://openaccess.thecvf.com/content/ICCV2021/papers/Kim_Continual_Learning_on_Noisy_Data_Streams_via_Self-Purified_Replay_ICCV_2021_paper.pdf
            if ".pdf" in url.lower():
                url = url.replace("papers", "html")
                url = url.replace(".pdf", ".html")
            res = requests.get(url)
            soup = BeautifulSoup(res.content, "html.parser")
            tmp_title = soup.find("div", {"id": "papertitle"}).text.replace("\n", "").strip()
            tmp_authors = soup.find("div", {"id": "authors"}).text.split(";")[0].strip().split(", ")
            tmp_conference = soup.find("div", {"id": "authors"}).text.split(";")[1].strip().split(", ")[0]
            tmp_year = soup.find("div", {"id": "authors"}).text.split(";")[1].strip().split(", ")[1]
            result_dict = {
                "source": "thecvf",
                "title": tmp_title if tmp_title else "",
                "authors": "\t".join(tmp_authors) if tmp_authors else "",
                "url": url,
                "conference": tmp_conference if tmp_conference else "",
                "year": tmp_year if tmp_year else "",
            }

        elif "acm" in url.lower():
            # https://dl.acm.org/doi/10.1145/3292500.333
            # https://dl.acm.org/doi/pdf/10.1145/3292500.3330997
            if "pdf" in url.lower():
                url = url.replace("pdf/", "")
            res = requests.get(url)
            soup = BeautifulSoup(res.content, "html.parser")
            tmp_title = soup.find("h1", class_="citation__title").text
            tmp_authors = [author['title'] for author in soup.find_all("a", class_="author-name")]
            tmp_conference = soup.find("span", class_="epub-section__title").text
            tmp_year = soup.find("span", class_="CitationCoverDate").text.split(" ")[-1]
            result_dict = {
                "source": "acm",
                "title": tmp_title if tmp_title else "",
                "authors": "\t".join(tmp_authors) if tmp_authors else "",
                "url": url,
                "conference": tmp_conference if tmp_conference else "",
                "year": tmp_year if tmp_year else "",
            }
        
        elif "mlr" in url.lower():
            # https://proceedings.mlr.press/v80/balestriero18b.html
            # https://proceedings.mlr.press/v80/balestriero18b/balestriero18b.pdf
            if "pdf" in url.lower():
                url = "/".join(url.split('/')[:-1])+".html"
            res = requests.get(url)
            soup = BeautifulSoup(res.content, "html.parser")
            tmp_title = soup.find("h1").text
            tmp_authors = [author.strip() for author in soup.find("span", class_="authors").text.replace(u'\xa0', u' ').split(", ")]
            tmp = soup.find("div", id="info").text.replace(u'\xa0', u' ').split(", ")
            tmp_conference = tmp[0]
            tmp_year = tmp[-1][:4]
            result_dict = {
                "source": "pmlr",
                "title": tmp_title if tmp_title else "",
                "authors": "\t".join(tmp_authors) if tmp_authors else "",
                "url": url,
                "conference": tmp_conference if tmp_conference else "",
                "year": tmp_year if tmp_year else "",
            }
        
        else:
            result_dict = {}

        if not result_dict:
            return None

        log.update(result_dict)
        added, original = await db_manager.add_paper(**log)
        return {
            "kind": "paper",
            "added": added,
            "original": original,
            "title": result_dict["title"],
            "url": result_dict["url"],
            "abstract": result_dict.get("abstract", ""),
        }