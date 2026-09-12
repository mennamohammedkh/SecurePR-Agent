"""
repository_tools.py
====================
Person 5 - RAG / Tools / UI Owner
Repository Context Tools.

لو Agent محتاج يعرف "الـfunction دي بتتستخدم فين"، الأدوات هنا بترجعله الكود
المرتبط من الـrepository (مش بس الـdiff بتاع الـPR)، وده مهم جدًا لتحسين جودة
الـcode review لأنه بيدي الـAgent Context عن باقي المشروع.

get_repository_context() هي الأداة اللي بتتوفر لباقي الفريق (نقطة الربط).
"""

from .github_tools import get_repository_file, get_changed_files


def get_repository_context(repo_name: str, pr_number: int, related_paths: list = None, ref: str = None) -> dict:
    """
    بتجمع Context من الـrepository حوالين الـPR: محتوى الملفات اللي اتغيرت،
    وأي ملفات تانية مرتبطة (related_paths) لو الـAgent محدد إنه محتاجها.

    Args:
        repo_name: اسم الـrepository بصيغة "owner/repo"
        pr_number: رقم الـPR
        related_paths: لستة اختيارية بمسارات ملفات تانية عايزين نجيب محتواها
                       (زي الملف اللي بيستخدم الـfunction اللي اتعدلت)
        ref: اسم الـbranch أو commit sha تجيب منه الملفات (افتراضيًا default branch)

    Returns:
        dict فيه:
            - "changed_files": الملفات اللي اتغيرت في الـPR (من get_changed_files)
            - "related_files": dict {path: content} للملفات المرتبطة المطلوبة
    """
    changed_files = get_changed_files(repo_name, pr_number)

    related_files = {}
    if related_paths:
        for path in related_paths:
            related_files[path] = get_repository_file(repo_name, path, ref=ref)

    return {
        "changed_files": changed_files,
        "related_files": related_files,
    }
