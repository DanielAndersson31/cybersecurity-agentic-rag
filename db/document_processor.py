import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from langchain_community.document_loaders import TextLoader, CSVLoader, JSONLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def process_document(file_path:str, file_type:str , chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """
    Process various document types and split them into manageable chunks.
    
    Args:
        file_path (str): Path to the document file
        file_type (str): Type of file ('text', 'csv', 'json', 'pdf')
        chunk_size (int): Size of each chunk
        chunk_overlap (int): Overlap between chunks
        
    Returns:
        List[Document]: List of document chunks with metadata
        
    Raises:
        ValueError: If file type is unsupported
        FileNotFoundError: If file doesn't exist
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    if file_type == "text":
        loader = TextLoader(file_path)
    elif file_type == "csv":
        loader = CSVLoader(file_path)
    elif file_type == "json":
        loader = JSONLoader(file_path)
    elif file_type == "pdf":
        loader = PyPDFLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
    try:
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = text_splitter.split_documents(documents)
    except Exception as e:
        raise ValueError(f"Error processing document: {e}")

    return chunks

def _process_prevention_pdfs(prevention_dir_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process Prevention Framework PDF documents."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not prevention_dir_path.exists():
        raise FileNotFoundError(f"Prevention documents directory {prevention_dir_path} does not exist.")
    
    if not prevention_dir_path.is_dir():
        raise NotADirectoryError(f"Prevention path {prevention_dir_path} is not a directory.")

    print(f"Processing Prevention documents from: {prevention_dir_path}")
    
    for pdf_file in prevention_dir_path.glob("*.pdf"):
        try:
            langchain_chunks = process_document(
                file_path=str(pdf_file), 
                file_type="pdf"
            )
            for i, chunk_doc in enumerate(langchain_chunks):
                doc_texts.append(chunk_doc.page_content)
                meta = {
                    **chunk_doc.metadata,
                    "agent_type": "prevention",
                    "doc_type": "framework_guide",
                    "source": pdf_file.name,
                    "chunk_id": i
                }
                metadatas_list.append(meta)
                chunk_base_id = f"prevention_{pdf_file.stem}_{i}"
                ids_list.append(chunk_base_id)
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Failed to process prevention PDF {pdf_file.name}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error processing {pdf_file.name}: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_incident_response_pdfs(ir_dir_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process Incident Response Playbook PDF documents."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not ir_dir_path.exists():
        raise FileNotFoundError(f"Incident Response documents directory {ir_dir_path} does not exist.")
    
    if not ir_dir_path.is_dir():
        raise NotADirectoryError(f"Incident Response path {ir_dir_path} is not a directory.")

    print(f"Processing Incident Response documents from: {ir_dir_path}")
    
    for pdf_file in ir_dir_path.glob("*.pdf"):
        try:
            langchain_chunks = process_document(
                file_path=str(pdf_file),
                file_type="pdf"
            )
            for i, chunk_doc in enumerate(langchain_chunks):
                doc_texts.append(chunk_doc.page_content)
                meta = {
                    **chunk_doc.metadata,
                    "agent_type": "incident_response",
                    "doc_type": "playbook",
                    "source": pdf_file.name,
                    "chunk_id": i
                }
                metadatas_list.append(meta)
                chunk_base_id = f"ir_{pdf_file.stem}_{i}"
                ids_list.append(chunk_base_id)
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Failed to process incident response PDF {pdf_file.name}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error processing {pdf_file.name}: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_mitre_attack_data(mitre_file_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process MITRE ATT&CK enterprise attack data."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not mitre_file_path.exists():
        raise FileNotFoundError(f"MITRE ATT&CK file {mitre_file_path} does not exist.")
    
    if not mitre_file_path.is_file():
        raise ValueError(f"MITRE ATT&CK path {mitre_file_path} is not a file.")

    print(f"Processing MITRE ATT&CK data from: {mitre_file_path.name}")
    
    try:
        with open(mitre_file_path, 'r', encoding='utf-8') as f:
            mitre_data = json.load(f)
        
        for obj in mitre_data.get('objects', []):
            if obj.get('type') == 'attack-pattern':
                technique_id = "Unknown"
                for ref in obj.get('external_references', []):
                    if ref.get('source_name') == 'mitre-attack':
                        technique_id = ref.get('external_id', 'Unknown')
                        break
                
                name = obj.get('name', '')
                description = obj.get('description', '')
                description = description.replace('\r\n', '\n').strip()

                text_content = f"MITRE ATT&CK Technique {technique_id}: {name}\n{description}"
                doc_texts.append(text_content)
                
                meta = {
                    "agent_type": "shared",
                    "doc_type": "technique",
                    "framework": "mitre_attack",
                    "technique_id": technique_id,
                    "source": mitre_file_path.name 
                }
                metadatas_list.append(meta)
                
                mitre_id = f"mitre_{technique_id.replace('.', '_').replace('-', '_')}"
                ids_list.append(mitre_id)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in MITRE ATT&CK file {mitre_file_path.name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing MITRE ATT&CK data: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_emerging_threats_ips(file_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process Emerging Threats IP blocklist from text file."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not file_path.exists():
        raise FileNotFoundError(f"Emerging Threats IP blocklist file {file_path} does not exist.")
    
    if not file_path.is_file():
        raise ValueError(f"Emerging Threats IP path {file_path} is not a file.")

    try:
        langchain_chunks = process_document(
            file_path=str(file_path),
            file_type="text"
        )
        for i, chunk_doc in enumerate(langchain_chunks):
            ip_address = chunk_doc.page_content.strip()
            
            if not ip_address or ip_address.startswith("#") or '.' not in ip_address:
                continue
                
            text_content = f"Blocked IP Address: {ip_address}"
            doc_texts.append(text_content)
            
            meta = {
                **chunk_doc.metadata, 
                "agent_type": "threat_intelligence",
                "doc_type": "ioc",
                "indicator_type": "ip_address",
                "source": file_path.name, 
                "raw_indicator": ip_address
            }
            metadatas_list.append(meta)
            
            emerging_ip_id = f"emerging_ip_{file_path.stem}_{i}"
            ids_list.append(emerging_ip_id)

    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"Failed to process Emerging Threats IP file {file_path.name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing {file_path.name}: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_feodo_tracker_ips(file_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process Feodo Tracker IP blocklist from JSON file."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not file_path.exists():
        raise FileNotFoundError(f"Feodo Tracker IP blocklist file {file_path} does not exist.")
    
    if not file_path.is_file():
        raise ValueError(f"Feodo Tracker IP path {file_path} is not a file.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ip_data_list = json.load(f)
        
        if not isinstance(ip_data_list, list):
            raise ValueError(f"Expected a list of IPs in {file_path.name}, but got {type(ip_data_list)}")
        
        for i, ip_info in enumerate(ip_data_list):
            ip_address = ip_info.get('ip_address')
            if not ip_address: 
                continue

            malware_family = ip_info.get('malware', 'Unknown')
            status = ip_info.get('status', 'Unknown')
            hostname = ip_info.get('hostname', 'N/A')
            country = ip_info.get('country', 'N/A')
            first_seen = ip_info.get('first_seen_utc', 'N/A')

            text_content = (
                f"Malicious IP (Feodo Tracker): {ip_address}, "
                f"Hostname: {hostname}, Malware family: {malware_family}, "
                f"Status: {status}, Country: {country}, First seen (UTC): {first_seen}"
            )
            doc_texts.append(text_content)
            
            meta = {
                "agent_type": "threat_intelligence",
                "doc_type": "ioc",
                "indicator_type": "ip_address",
                "source": file_path.name,
                "raw_indicator": ip_address,
                "hostname": hostname,
                "malware_family": malware_family,
                "ip_status": status,
                "country": country,
                "first_seen_utc": first_seen
            }
            metadatas_list.append(meta)
            
            feodo_id = f"feodo_ip_{ip_address.replace('.', '_')}_{i}"
            ids_list.append(feodo_id)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in Feodo Tracker file {file_path.name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing {file_path.name}: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_cisa_vulnerabilities(file_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process CISA Known Exploited Vulnerabilities from JSON file."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not file_path.exists():
        raise FileNotFoundError(f"CISA KEV file {file_path} does not exist.")
    
    if not file_path.is_file():
        raise ValueError(f"CISA KEV path {file_path} is not a file.")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            cisa_data = json.load(f)
        
        vulnerabilities_list = cisa_data.get('vulnerabilities', [])
        
        if not isinstance(vulnerabilities_list, list):
            raise ValueError(f"Expected a list under 'vulnerabilities' key in {file_path.name}, but found {type(vulnerabilities_list)}")
        
        for i, vuln in enumerate(vulnerabilities_list):
            cve_id = vuln.get('cveID')
            if not cve_id:
                continue

            name = vuln.get('vulnerabilityName', 'N/A')
            description = vuln.get('shortDescription', 'N/A')
            date_added = vuln.get('dateAdded', 'N/A')
            ransomware_use = vuln.get('knownRansomwareUse', 'N/A')
            due_date = vuln.get('dueDate', 'N/A') 
            notes = vuln.get('notes', 'N/A')

            text_content = (
                f"CISA KEV: {cve_id} - {name}. Description: {description}. "
                f"Date Added: {date_added}. Known Ransomware Use: {ransomware_use}. "
                f"Due Date (Federal): {due_date}."
                f"{(' Notes: ' + notes) if notes != 'N/A' and notes else ''}"
            )
            doc_texts.append(text_content)
            
            meta = {
                "agent_type": "threat_intelligence",
                "doc_type": "vulnerability",
                "indicator_type": "cve_id", 
                "source": file_path.name,
                "cve_id": cve_id,
                "vulnerability_name": name,
                "date_added": date_added,
                "known_ransomware_use": ransomware_use,
                "due_date": due_date,
                "notes": notes
            }
            metadatas_list.append(meta)
            
            cisa_id = f"cisa_kev_{cve_id.replace('-', '_').upper()}"
            ids_list.append(cisa_id)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in CISA KEV file {file_path.name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing {file_path.name}: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_urlhaus_links(file_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process URLHaus malicious URL links from CSV file."""
    doc_texts = []
    metadatas_list = []
    ids_list = []

    if not file_path.exists():
        raise FileNotFoundError(f"URLHaus CSV file {file_path} does not exist.")
    
    if not file_path.is_file():
        raise ValueError(f"URLHaus path {file_path} is not a file.")

    try:
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            actual_content_pos = 0
            while True:
                line = f.readline()
                if not line: 
                    break 
                if line.startswith('#'):
                    actual_content_pos = f.tell() 
                else:
                    f.seek(actual_content_pos) 
                    break
            
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                # Limit to 5000 entries for testing purposes
                if len(doc_texts) >= 5000:
                    print("Reached limit of 5000 URLHaus entries for testing")
                    break
                entry_id = row.get('# id', row.get('id'))
                if not entry_id:
                    continue

                url = row.get('url', 'N/A')
                threat_type = row.get('threat', 'N/A')
                tags = row.get('tags', 'N/A')
                date_added = row.get('dateadded', 'N/A')
                url_status = row.get('url_status', 'N/A')
                reporter = row.get('reporter', 'N/A')

                text_content = (
                    f"Malicious URL (URLHaus): {url}, Threat: {threat_type}, "
                    f"Status: {url_status}, Tags: {tags}, Reported: {date_added} "
                    f"by {reporter}."
                )
                doc_texts.append(text_content)
                
                meta = {
                    "agent_type": "threat_intelligence",
                    "doc_type": "ioc",
                    "indicator_type": "url",
                    "source": file_path.name,
                    "raw_url": url,
                    "threat_type": threat_type,
                    "url_status": url_status,
                    "tags": tags,
                    "date_added": date_added,
                    "reporter": reporter,
                    "entry_id": entry_id 
                }
                metadatas_list.append(meta)
                
                urlhaus_id = f"urlhaus_{entry_id}"
                ids_list.append(urlhaus_id)
    
    except csv.Error as e:
        raise ValueError(f"Error processing CSV file {file_path.name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing {file_path.name}: {e}") from e
    
    return doc_texts, metadatas_list, ids_list

def _process_threat_intelligence_data(threat_dir_path: Path) -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Process all threat intelligence data sources."""
    all_doc_texts = []
    all_metadatas = []
    all_ids = []

    if not threat_dir_path.exists():
        raise FileNotFoundError(f"Threat Intelligence directory {threat_dir_path} does not exist.")
    
    if not threat_dir_path.is_dir():
        raise NotADirectoryError(f"Threat Intelligence path {threat_dir_path} is not a directory.")

    print(f"\nProcessing Threat Intelligence data from: {threat_dir_path}")

    # Process each threat intelligence source
    emerging_texts, emerging_metas, emerging_ids = _process_emerging_threats_ips(threat_dir_path / "emerging-Block-IPs.txt")
    all_doc_texts.extend(emerging_texts)
    all_metadatas.extend(emerging_metas)
    all_ids.extend(emerging_ids)

    feodo_texts, feodo_metas, feodo_ids = _process_feodo_tracker_ips(threat_dir_path / "ipblocklist.json")
    all_doc_texts.extend(feodo_texts)
    all_metadatas.extend(feodo_metas)
    all_ids.extend(feodo_ids)

    cisa_texts, cisa_metas, cisa_ids = _process_cisa_vulnerabilities(threat_dir_path / "known_exploited_vulnerabilities.json")
    all_doc_texts.extend(cisa_texts)
    all_metadatas.extend(cisa_metas)
    all_ids.extend(cisa_ids)

    urlhaus_texts, urlhaus_metas, urlhaus_ids = _process_urlhaus_links(threat_dir_path / "urlhaus_links.csv")
    all_doc_texts.extend(urlhaus_texts)
    all_metadatas.extend(urlhaus_metas)
    all_ids.extend(urlhaus_ids)
    
    mitre_texts, mitre_metas, mitre_ids = _process_mitre_attack_data(threat_dir_path  / "mitre-enterprise-attack.json")
    all_doc_texts.extend(mitre_texts)
    all_metadatas.extend(mitre_metas)
    all_ids.extend(mitre_ids)
    
    return all_doc_texts, all_metadatas, all_ids

def process_all_documents(data_dir: str = "data/documents") -> tuple[List[str], List[Dict[str, Any]], List[str]]:
    """
    Processes all specified documents from the data directory, 
    chunks them, and prepares them for database ingestion.

    Args:
        data_dir (str): The root directory containing the raw data.

    Returns:
        tuple[List[str], List[Dict[str, Any]], List[str]]: 
            A tuple containing lists of document contents, metadatas, and ids.
    """
    all_doc_texts = []
    all_metadatas = []
    all_ids = []

    data_path = Path(data_dir)

    # Process Prevention Framework documents
    prevention_texts, prevention_metas, prevention_ids = _process_prevention_pdfs(data_path / "framework_basics")
    all_doc_texts.extend(prevention_texts)
    all_metadatas.extend(prevention_metas)
    all_ids.extend(prevention_ids)

    # Process Incident Response Playbooks
    ir_texts, ir_metas, ir_ids = _process_incident_response_pdfs(data_path / "incident_response")
    all_doc_texts.extend(ir_texts)
    all_metadatas.extend(ir_metas)
    all_ids.extend(ir_ids)

    # Process Threat Intelligence data
    threat_texts, threat_metas, threat_ids = _process_threat_intelligence_data(data_path / "threat_intelligence")
    all_doc_texts.extend(threat_texts)
    all_metadatas.extend(threat_metas)
    all_ids.extend(threat_ids)

    print(f"Finished processing all documents. Total texts: {len(all_doc_texts)}, Metadatas: {len(all_metadatas)}, IDs: {len(all_ids)}")
    return all_doc_texts, all_metadatas, all_ids
 
 
    
