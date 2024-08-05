from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from stockfish import Stockfish
import chess
import chess.pgn
import time
import os


def login_chess_com(driver, username, password):
    driver.get('https://www.chess.com/login_and_go')
    WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'input[aria-label="Username or Email"]')))
    username_input = driver.find_element(
        By.CSS_SELECTOR, 'input[aria-label="Username or Email"]')
    username_input.send_keys(username)
    password_input = driver.find_element(
        By.CSS_SELECTOR, 'input[aria-label="Password"]')
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, 'div.home-user-info')))


def navigate_to_game_page(driver, game_url):
    driver.get(game_url)
    time.sleep(5)
    switch_element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'label.ui_v5-switch-label[for="evaluationExplorer"]'))
    )
    switch_element.click()
    time.sleep(2)


def extract_moves(driver):
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    moves_container = soup.find(
        'wc-horizontal-move-list-play-explorer', class_='explorer-moves-hml')
    moves = []
    if moves_container:
        move_elements = moves_container.find_all('span', class_='move-node')
        for move in move_elements:
            move_text = move.find('span', class_='move-text')
            figurine = move_text.find(
                'span', class_='icon-font-chess') if move_text else None
            if figurine:
                figurine_text = figurine['data-figurine']
                move_text_value = f"{figurine_text}{move_text.text.strip()}"
            else:
                move_text_value = move_text.text.strip() if move_text else ''
            if move_text_value:
                moves.append(move_text_value)
    return moves

def describe_move(move_uci, stockfish):
    piece = stockfish.get_what_is_on_square(move_uci[:2]) # returns Stockfish.Piece.WHITE_KING
    only_piece = str(piece).split('.')[1]
    # piece = piece_map.get(move_uci[0], 'Unknown Piece')
    from_square = move_uci[:2]
    to_square = move_uci[2:]
    
    # Convert UCI square to algebraic notation
    from_square_algebraic = chess.square_name(chess.parse_square(from_square))
    to_square_algebraic = chess.square_name(chess.parse_square(to_square))
    
    return f"'{only_piece}' from {from_square_algebraic} to {to_square_algebraic}"

def san_to_coord_moves(moves):
    board = chess.Board()
    coord_moves = []
    for move in moves:
        board_move = board.parse_san(move)
        coord_moves.append(board_move.uci())
        board.push(board_move)
    return coord_moves, board

def analyze_with_stockfish(moves, stockfish_path):
    if not os.path.isfile(stockfish_path):
        print(f"Stockfish binary not found at {stockfish_path}")
        return None, None
    stockfish = Stockfish(stockfish_path)
    stockfish.set_skill_level(20)
    stockfish.set_position(moves) 
    # stockfish.make_moves_from_current_position(moves)  # Feeding the moves
    best_move = stockfish.get_best_move()
    top_3_moves = stockfish.get_top_moves(3)
    descriptive_move = describe_move(best_move, stockfish) if best_move else None
    return best_move, top_3_moves, descriptive_move

def monitor_game(driver, stockfish_path):
    moves = extract_moves(driver)
    coord_moves, board= san_to_coord_moves(moves)
    best_move, top_3_moves, descriptive_move = analyze_with_stockfish(coord_moves, stockfish_path)
    print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")
    print(f"Best move: {best_move}")
    print(f"Descriptive move: {descriptive_move}")

    print(f"top_3_moves:")
    for x in top_3_moves:
        print(x)

    last_move = moves[-1] if moves else None

    while True:
        try:
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            current_move_element = soup.find('span', class_='move-san-san')
            current_move = current_move_element.text.strip() if current_move_element else None
            # If there's a new move, update the moves list and re-analyze
            if current_move and current_move != last_move:
                moves.append(current_move)
                coord_moves, board = san_to_coord_moves(moves)
                best_move, top_3_moves, descriptive_move = analyze_with_stockfish(coord_moves, stockfish_path)
                last_move = current_move
                print("--------------------------------------------------------")
                print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")
                print(f"Best move: {best_move}")
                print(f"Descriptive move: {descriptive_move}")
                print(f"top_3_moves:")
                for x in top_3_moves:
                    print(x)
        except Exception as e:
            print(f"An error occurred: {e}")
            break

def main(username, password, game_id, stockfish_path):
    game_url = f'https://www.chess.com/game/live/{game_id}'
    driver = webdriver.Chrome()
    try:
        login_chess_com(driver, username, password)
        navigate_to_game_page(driver, game_url)
        monitor_game(driver, stockfish_path)
    finally:
        driver.quit()

    


if __name__ == "__main__":
    username = 'YOUR_USERNAME'
    password = 'YOUR_PASSWORD'
    game_id = 'GAME_ID'
    stockfish_path = 'stockfish_path'
    main(username, password, game_id, stockfish_path)
