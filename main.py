import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(BASE_DIR, "data")

def ensure_data_dir():
    if not os.path.exists(DEFAULT_DATA_DIR):
        try:
            os.makedirs(DEFAULT_DATA_DIR)
        except OSError:
            pass

def run_script(script_path, pause=True):
    if not os.path.exists(script_path):
        print(f"\n[Error] File not found: {script_path}")
        time.sleep(1)
        return

    print(f"\n>>> Running: {os.path.basename(script_path)}")
    print("-" * 40)
    
    env = os.environ.copy()
    env["PROJECT_DATA_DIR"] = DEFAULT_DATA_DIR
    
    try:
        subprocess.run([sys.executable, script_path], env=env, check=False)
    except KeyboardInterrupt:
        print("\n[!] Interrupted.")
    except Exception as e:
        print(f"\n[Error] {e}")
    
    print("-" * 40)
    if pause:
        input("Press Enter to continue...")
    else:
        time.sleep(1)

def list_and_select(directory):
    if not os.path.exists(directory):
        print(f"\n[Error] Directory not found: {directory}")
        input("Press Enter to back...")
        return

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"Directory: {os.path.basename(directory)}\n")
        
        files = sorted([f for f in os.listdir(directory) if f.endswith('.py') and f != '__init__.py'])
        
        if not files:
            print("No Python scripts found.")
            input("Press Enter to back...")
            return

        for i, f in enumerate(files, 1):
            print(f"{i}. {f}")
        
        print("\n0. Back")
        
        choice = input("\nSelect file: ").strip()
        
        if choice == '0':
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                run_script(os.path.join(directory, files[idx]))
            else:
                print("Invalid selection.")
                time.sleep(0.5)
        except ValueError:
            print("Invalid input.")
            time.sleep(0.5)

def run_automatic_mode(base_dir):
    os.system('clear' if os.name == 'posix' else 'cls')
    print("--- Automatic Pipeline ---")
    
    print("\n[Step 1/6] Crawling Data")
    ans = input("Do you want to run crawlers? (y/n): ").strip().lower()
    
    if ans == 'y':
        crawlers_dir = os.path.join(base_dir, "crawlers")
        files = sorted([f for f in os.listdir(crawlers_dir) if f.endswith('.py') and f != '__init__.py'])
        
        if not files:
            print("No crawlers found.")
        else:
            print(f"Running {len(files)} crawlers sequentially...")
            for f in files:
                run_script(os.path.join(crawlers_dir, f), pause=False)

    print("\n[Step 2/6] Cleaning & Normalizing Data...")
    run_script(os.path.join(base_dir, "parser", "content_cleaner.py"), pause=False)

    print("\n[Step 3/6] Building Inverted Index...")
    run_script(os.path.join(base_dir, "index", "index_builder.py"), pause=False)

    print("\n[Step 4/6] Building Graph & Calculating PageRank...")
    run_script(os.path.join(base_dir, "graph", "graph_builder.py"), pause=False)

    print("\n[Step 5/6] Search Engine Core")
    print("Skipping interactive search in automatic mode.")
    print("You can test it manually from the main menu.")

    print("\n[Step 6/6] Launching Fake News Detector (LLM)...")
    llm_script = os.path.join(base_dir, "llm", "fake_news_detector.py")
    if os.path.exists(llm_script):
        run_script(llm_script, pause=True)
    else:
        print("LLM module not found yet.")
        input("Press Enter to finish...")

def main_menu():
    ensure_data_dir()
    
    crawlers_dir = os.path.join(BASE_DIR, "crawlers")
    parser_dir = os.path.join(BASE_DIR, "parser")
    index_dir = os.path.join(BASE_DIR, "index")
    graph_dir = os.path.join(BASE_DIR, "graph")
    search_dir = os.path.join(BASE_DIR, "search")
    llm_dir = os.path.join(BASE_DIR, "llm")
    
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"Project Root: {BASE_DIR}")
        print(f"Data Path:    {DEFAULT_DATA_DIR}\n")
        
        print("1. Crawlers      (Data Acquisition)")
        print("2. Parser        (Data Cleaning)")
        print("3. Indexer       (Build Index)")
        print("4. Graph         (Build Graph & PageRank)")
        print("5. Search Engine (Interactive Test)")
        print("6. Detector      (LLM Fake News Detection)")
        print("7. Auto Pipeline (Run All Steps)")
        print("\n0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '0':
            print("Goodbye!")
            break
            
        elif choice == '1':
            list_and_select(crawlers_dir)
        elif choice == '2':
            list_and_select(parser_dir)
        elif choice == '3':
            list_and_select(index_dir)
        elif choice == '4':
            list_and_select(graph_dir)
        elif choice == '5':
            list_and_select(search_dir)
        elif choice == '6':
            list_and_select(llm_dir)
        elif choice == '7':
            run_automatic_mode(BASE_DIR)
        else:
            print("Invalid option.")
            time.sleep(0.5)

if __name__ == "__main__":
    main_menu()
