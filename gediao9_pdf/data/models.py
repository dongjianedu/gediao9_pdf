from dataclasses import dataclass, field


@dataclass
class InterviewData:
    guest: str = ""
    interviewer: str = ""
    date: str = ""
    bio: str = ""
    full_text: str = ""
    image_dir: str = ""

    part1: str = ""
    part2: str = ""

    part1_qa: list = field(default_factory=list)
    part2_qa: list = field(default_factory=list)