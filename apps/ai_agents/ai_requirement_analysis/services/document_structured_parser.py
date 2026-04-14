"""
文档解析服务 - 支持解析文档的层级标题结构
"""
import os
import re
import logging
from typing import List, Dict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StructuredDocumentParser(ABC):
    """结构化文档解析器基类 - 支持层级标题解析"""
    
    @abstractmethod
    def parse_structured(self, file_path: str) -> Dict:
        """
        解析文档，返回结构化数据
        返回格式：
        {
            'title': '文档标题',
            'sections': [
                {
                    'title': '1级标题',
                    'level': 1,
                    'content': '内容',
                    'subsections': [
                        {
                            'title': '2级标题',
                            'level': 2,
                            'content': '内容',
                            'subsections': []
                        }
                    ]
                }
            ]
        }
        """
        pass


class TextStructuredParser(StructuredDocumentParser):
    """纯文本文件结构化解析器"""
    
    def parse_structured(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取文档标题（第一行非空内容）
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            title = lines[0] if lines else os.path.splitext(os.path.basename(file_path))[0]
            
            # 解析层级结构
            sections = self._parse_text_sections(content)
            
            return {
                'title': title,
                'sections': sections
            }
        except Exception as e:
            logger.error(f"文本文件结构化解析失败: {str(e)}", exc_info=True)
            raise
    
    def _parse_text_sections(self, content: str) -> List[Dict]:
        """解析文本中的层级标题"""
        sections = []
        current_section = None
        current_subsection = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 检测1级标题（# 标题 或 一、标题）
            level1_match = re.match(r'^(?:#+\s+|一[、.]\s*|1[、.]\s*)(.+)', line)
            # 检测2级标题（## 标题 或 （一）标题 或 1.1 标题）
            level2_match = re.match(r'^(?:##\s+|（[一二三四五六七八九十]+）\s*|1\.\d+\s*)(.+)', line)
            
            if level1_match and not level2_match:
                # 1级标题
                if current_section:
                    if current_subsection:
                        current_section['subsections'].append(current_subsection)
                        current_subsection = None
                    sections.append(current_section)
                current_section = {
                    'title': level1_match.group(1).strip(),
                    'level': 1,
                    'content': '',
                    'subsections': []
                }
            elif level2_match:
                # 2级标题
                if current_section:
                    if current_subsection:
                        current_section['subsections'].append(current_subsection)
                    current_subsection = {
                        'title': level2_match.group(1).strip(),
                        'level': 2,
                        'content': '',
                        'subsections': []
                    }
                else:
                    # 如果没有1级标题，创建一个默认的
                    current_section = {
                        'title': '概述',
                        'level': 1,
                        'content': '',
                        'subsections': []
                    }
                    current_subsection = {
                        'title': level2_match.group(1).strip(),
                        'level': 2,
                        'content': '',
                        'subsections': []
                    }
            else:
                # 普通内容
                if current_subsection:
                    current_subsection['content'] += line + '\n'
                elif current_section:
                    current_section['content'] += line + '\n'
        
        # 添加最后一个节点
        if current_subsection:
            if current_section:
                current_section['subsections'].append(current_subsection)
        if current_section:
            sections.append(current_section)
        
        return sections


class MarkdownStructuredParser(StructuredDocumentParser):
    """Markdown 文件结构化解析器"""
    
    def parse_structured(self, file_path: str) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取文档标题（第一个 # 标题）
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else os.path.splitext(os.path.basename(file_path))[0]
            
            sections = self._parse_markdown_sections(content)
            
            return {
                'title': title,
                'sections': sections
            }
        except Exception as e:
            logger.error(f"Markdown 文件结构化解析失败: {str(e)}", exc_info=True)
            raise
    
    def _parse_markdown_sections(self, content: str) -> List[Dict]:
        """解析 Markdown 中的层级标题"""
        sections = []
        current_section = None
        current_subsection = None
        current_content = []
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # 检测1级标题
            if re.match(r'^#\s+(.+)', line):
                # 保存上一个节点
                if current_subsection:
                    current_subsection['content'] = '\n'.join(current_content).strip()
                    if current_section:
                        current_section['subsections'].append(current_subsection)
                    current_subsection = None
                elif current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                current_section = {
                    'title': re.match(r'^#\s+(.+)', line).group(1).strip(),
                    'level': 1,
                    'content': '',
                    'subsections': []
                }
                current_content = []
            
            # 检测2级标题
            elif re.match(r'^##\s+(.+)', line):
                # 保存上一个子节点
                if current_subsection:
                    current_subsection['content'] = '\n'.join(current_content).strip()
                    if current_section:
                        current_section['subsections'].append(current_subsection)
                
                current_subsection = {
                    'title': re.match(r'^##\s+(.+)', line).group(1).strip(),
                    'level': 2,
                    'content': '',
                    'subsections': []
                }
                current_content = []
            
            else:
                current_content.append(line)
        
        # 保存最后一个节点
        if current_subsection:
            current_subsection['content'] = '\n'.join(current_content).strip()
            if current_section:
                current_section['subsections'].append(current_subsection)
        elif current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        return sections


class DocxStructuredParser(StructuredDocumentParser):
    """Word 文档结构化解析器"""
    
    def parse_structured(self, file_path: str) -> Dict:
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValueError(f"文件大小为 0: {file_path}")
            
            logger.info(f"开始解析 Word 文档: {file_path}, 大小: {file_size} bytes")
            
            from docx import Document
            
            doc = Document(file_path)
            
            # 提取文档标题（第一个非空段落）
            title = None
            sections = []
            current_section = None
            current_subsection = None
            current_content = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                # 检查段落样式判断标题级别
                style_name = para.style.name.lower() if para.style else ''
                
                # 1级标题：Heading 1 或以 # 开头
                if 'heading 1' in style_name or (text.startswith('#') and not text.startswith('##')):
                    # 保存上一个节点
                    if current_subsection:
                        current_subsection['content'] = '\n'.join(current_content).strip()
                        if current_section:
                            current_section['subsections'].append(current_subsection)
                        current_subsection = None
                    elif current_section:
                        current_section['content'] = '\n'.join(current_content).strip()
                        sections.append(current_section)
                    
                    # 设置文档标题
                    if title is None:
                        title = text.lstrip('#').strip()
                    
                    current_section = {
                        'title': text.lstrip('#').strip(),
                        'level': 1,
                        'content': '',
                        'subsections': []
                    }
                    current_content = []
                
                # 2级标题：Heading 2 或以 ## 开头
                elif 'heading 2' in style_name or text.startswith('##'):
                    # 保存上一个子节点
                    if current_subsection:
                        current_subsection['content'] = '\n'.join(current_content).strip()
                        if current_section:
                            current_section['subsections'].append(current_subsection)
                    
                    current_subsection = {
                        'title': text.lstrip('#').strip(),
                        'level': 2,
                        'content': '',
                        'subsections': []
                    }
                    current_content = []
                
                else:
                    # 普通内容
                    current_content.append(text)
            
            # 保存最后一个节点
            if current_subsection:
                current_subsection['content'] = '\n'.join(current_content).strip()
                if current_section:
                    current_section['subsections'].append(current_subsection)
            elif current_section:
                current_section['content'] = '\n'.join(current_content).strip()
                sections.append(current_section)
            
            # 如果没有标题，使用文件名
            if title is None:
                title = os.path.splitext(os.path.basename(file_path))[0]
            
            logger.info(f"Word 文档结构化解析完成，共 {len(sections)} 个1级章节")
            
            return {
                'title': title,
                'sections': sections
            }
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {str(e)}")
            raise
        except ValueError as e:
            logger.error(f"文件无效: {str(e)}")
            raise
        except ImportError:
            logger.error("python-docx 未安装，请运行: pip install python-docx")
            raise
        except Exception as e:
            logger.error(f"Word 文档结构化解析失败: {str(e)}", exc_info=True)
            raise


class DocumentStructuredParserFactory:
    """结构化文档解析器工厂"""
    
    PARSERS = {
        '.txt': TextStructuredParser,
        '.md': MarkdownStructuredParser,
        '.docx': DocxStructuredParser,
    }
    
    @classmethod
    def get_parser(cls, file_path: str) -> StructuredDocumentParser:
        """根据文件扩展名获取对应的解析器"""
        ext = os.path.splitext(file_path)[1].lower()
        parser_class = cls.PARSERS.get(ext)
        
        if not parser_class:
            raise ValueError(f"不支持的文件格式: {ext}")
        
        return parser_class()
    
    @classmethod
    def parse_file(cls, file_path: str) -> Dict:
        """解析文件，返回结构化数据"""
        parser = cls.get_parser(file_path)
        return parser.parse_structured(file_path)
