from rich.table import Table

def _build_table(title: str, color: str) -> Table:
  table = Table(
    title=title,
    style=color,
    width=78,
    title_style="bold white"
  )
  table.add_column("Name", width=37)
  table.add_column("Type", width=16)
  table.add_column("Privacy", width=13)
  table.add_column("Activity", width=12)
  return table

class Tables:
  happy_repos: Table
  repos_missing_commits: Table
  repos_missing_git_hooks: Table
  repos_missing_upstream: Table
  repos_with_unpulled_commits: Table
  repos_with_unpushed_commits: Table
  repos_with_untracked_files: Table
  not_repos: Table

  def __init__(self):
    self.happy_repos = _build_table(
      title="Happy Repos",
      color="#22C55E"
    )
    self.repos_missing_git_hooks = _build_table(
      title="Repos missing Git Hooks",
      color="#00FFEA"
    )
    self.repos_with_unpushed_commits = _build_table(
      title="Repos with Unpushed Commits",
      color="#FFD700"
    )
    self.repos_missing_commits = _build_table(
      title="Repos missing Commits",
      color="#FFA500"
    )
    self.repos_with_untracked_files = _build_table(
      title="Repos with Untracked Files",
      color="#FFA500"
    )
    self.repos_with_unpulled_commits = _build_table(
      title="Repos that are behind Upstream",
      color="#FFA500"
    )
    self.repos_missing_upstream = _build_table(
      title="Repos missing an Upstream",
      color="#DC143C"
    )
    self.not_repos = Table(
      title="Not a Repo",
      style="#DC143C",
      width=37
    )
    self.not_repos.add_column("Name")

  def get_all_tables(self) -> list[Table]:
    return [
      self.happy_repos,
      self.repos_missing_commits,
      self.repos_missing_git_hooks,
      self.repos_missing_upstream,
      self.repos_with_unpulled_commits,
      self.repos_with_unpushed_commits,
      self.repos_with_untracked_files,
      self.not_repos
    ]

