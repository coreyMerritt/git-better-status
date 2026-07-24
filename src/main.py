#!/usr/bin/env python
import argparse
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from pathlib import Path

import git
from github import Github
from github.Auth import Token
from github.Repository import Repository
from rich.console import Console
from rich.table import Table
from rich.text import Text

from models.archived_map import ARCHIVED_MAP
from models.private_color_map import PRIVATE_COLOR_MAP
from models.project_type_map import PROJECT_TYPE_MAP
from models.tables import Tables


def main(path: Path, github_token: Token) -> None:
  github_session = Github(auth=github_token)
  tables = Tables()
  repos = __build_repo_dicts(
    path=path,
    not_repos_table=tables.not_repos
  )
  with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
    list(executor.map(
      __categorize_project,
      repos.keys(),
      repos.values(),
      repeat(tables),
      repeat(github_session)
    ))
  with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
    list(executor.map(
      __sort_table,
      tables.get_all_tables()
    ))
  __output_results(tables)

def __build_repo_dicts(path: Path, not_repos_table: Table) -> dict[Path, git.Repo]:
  repos: dict[Path, git.Repo] = {}
  IS_SINGLE_PROJECT = (path / ".git").exists()
  if IS_SINGLE_PROJECT:
    project_path = path
    repos[project_path] = git.Repo(project_path)
  else:
    projects_path = path
    for project_path in sorted(projects_path.iterdir()):
      try:
        repos[project_path] = git.Repo(project_path)
      except git.InvalidGitRepositoryError:
        not_repos_table.add_row(project_path.resolve().name)
  return repos

def __categorize_project(project_path: Path, repo: git.Repo, tables: Tables, github_session: Github) -> None:
  project_name = project_path.resolve().name
  try:
    repo.remotes.origin.fetch()
  except AttributeError:
    __add_row(
      project_name=project_name,
      table=tables.repos_missing_upstream,
      github_repo=None
    )
    return
  github_repo = __get_github_repo(repo=repo, session=github_session)
  happy_repo = True
  IS_MISSING_UPSTREAM = len(repo.remote().refs) == 0
  if IS_MISSING_UPSTREAM:
    __add_row(
      project_name=project_name,
      table=tables.repos_missing_upstream,
      github_repo=github_repo
    )
    happy_repo = False
  HAS_UNTRACKED_FILES = len(repo.untracked_files) > 0
  if HAS_UNTRACKED_FILES:
    __add_row(
      project_name=project_name,
      table=tables.repos_with_untracked_files,
      github_repo=github_repo
    )
    happy_repo = False
  status = repo.git.status()
  HAS_UNPULLED_COMMITS = "Your branch is behind " in status
  if HAS_UNPULLED_COMMITS:
    __add_row(
      project_name=project_name,
      table=tables.repos_with_unpulled_commits,
      github_repo=github_repo
    )
    happy_repo = False
  HAS_UNPUSHED_COMMITS = "Your branch is ahead of " in status
  if HAS_UNPUSHED_COMMITS:
    __add_row(
      project_name=project_name,
      table=tables.repos_with_unpushed_commits,
      github_repo=github_repo
    )
    happy_repo = False
  IS_MISSING_COMMITS = "nothing to commit" not in status
  if IS_MISSING_COMMITS:
    __add_row(
      project_name=project_name,
      table=tables.repos_missing_commits,
      github_repo=github_repo
    )
    happy_repo = False
  HAS_GIT_HOOKS = all((Path(repo.git_dir) / "hooks" / h).exists() for h in (
    "pre-commit",
    "post-commit",
    "pre-push"
  ))
  if not HAS_GIT_HOOKS:
    __add_row(
      project_name=project_name,
      table=tables.repos_missing_git_hooks,
      github_repo=github_repo
    )
    happy_repo = False
  if happy_repo:
    __add_row(
      project_name=project_name,
      table=tables.happy_repos,
      github_repo=github_repo
    )

def __add_row(project_name: str, table: Table, github_repo: Repository | None) -> None:
  project_type = __get_project_type(github_repo)
  project_type_text = project_type["text"]
  project_type_color = project_type["color"]
  project_type_string = f"[{project_type_color}]{project_type_text}[/{project_type_color}]"
  if github_repo:
    private_color = PRIVATE_COLOR_MAP[str(github_repo.private)]["color"]
    private_text = PRIVATE_COLOR_MAP[str(github_repo.private)]["text"]
    archived_color = ARCHIVED_MAP[str(github_repo.archived)]["color"]
    archived_text = ARCHIVED_MAP[str(github_repo.archived)]["text"]
  else:
    private_color = "#DC143C"
    private_text = "Undefined"
    archived_color = "#DC143C"
    archived_text = "Undefined"
  private_string = f"[{private_color}]{private_text}[/{private_color}]"
  archived_string = f"[{archived_color}]{archived_text}[/{archived_color}]"
  table.add_row(
    project_name,
    project_type_string,
    private_string,
    archived_string
  )

def __get_github_repo(repo: git.Repo, session: Github) -> Repository:
  owner = __get_repo_owner(repo)
  name = __get_repo_name(repo)
  return session.get_repo(f"{owner}/{name}")

def __get_repo_owner(repo: git.Repo) -> str:
  url = repo.remotes.origin.url
  if url.endswith(".git"):
    url = url[:-4]
  match = re.search(r"[:/]([^/:]+)/([^/]+)$", url)
  assert match, f"Could not parse owner/repo from: {url}"
  return match.group(1)

def __get_repo_name(repo: git.Repo) -> str:
  url = repo.remotes.origin.url
  if url.endswith(".git"):
    url = url[:-4]
  match = re.search(r"[:/]([^/:]+)/([^/]+)$", url)
  assert match, f"Could not parse owner/repo from: {url}"
  return match.group(2)

def __get_project_type(gh_repo: Repository | None) -> dict:
  if gh_repo is None:
    return PROJECT_TYPE_MAP[None]
  for tag in gh_repo.get_topics():
    try:
      return PROJECT_TYPE_MAP[tag]
    except KeyError:
      pass
  return PROJECT_TYPE_MAP[None]

def __sort_table(table: Table) -> None:
  if not table.columns:
    return
  rows = list(zip(*(column._cells for column in table.columns)))  # pylint: disable=protected-access
  def sort_key(row: tuple) -> tuple:
    return tuple(Text.from_markup(str(cell)).plain.lower() for cell in row)
  rows.sort(key=sort_key)
  sorted_columns = list(zip(*rows))
  for column, sorted_cells in zip(table.columns, sorted_columns):
    column._cells = list(sorted_cells)  # pylint: disable=protected-access

def __output_results(tables: Tables) -> None:
  console = Console()
  print()
  if len(tables.happy_repos.rows) > 0:
    console.print(tables.happy_repos)
    print()
  if len(tables.repos_missing_git_hooks.rows) > 0:
    console.print(tables.repos_missing_git_hooks)
    print()
  if len(tables.repos_with_unpushed_commits.rows) > 0:
    console.print(tables.repos_with_unpushed_commits)
    print()
  if len(tables.repos_missing_commits.rows) > 0:
    console.print(tables.repos_missing_commits)
    print()
  if len(tables.repos_with_untracked_files.rows) > 0:
    console.print(tables.repos_with_untracked_files)
    print()
  if len(tables.repos_with_unpulled_commits.rows) > 0:
    console.print(tables.repos_with_unpulled_commits)
    print()
  if len(tables.repos_missing_upstream.rows) > 0:
    console.print(tables.repos_missing_upstream)
    print()
  if len(tables.not_repos.rows) > 0:
    console.print(tables.not_repos)
    print()


if __name__ == "__main__":
  logging.getLogger("github").setLevel(logging.CRITICAL)
  parser = argparse.ArgumentParser()
  parser.add_argument("projects_path", type=str)
  args = parser.parse_args()
  main(
    path=Path(args.projects_path),
    github_token=Token(os.environ["GITHUB_PAT"])
  )
