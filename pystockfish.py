"""
    pystockfish
    ~~~~~~~~~~~~~~~

    Wraps the Stockfish chess engine.  Assumes stockfish is
    executable at the root level.

    Built on Ubuntu 12.1 tested with Stockfish 120212.
    
    :copyright: (c) 2013 by Jarret Petrillo.
    :license: GNU General Public License, see LICENSE for more details.
"""

import subprocess
from random import randint

import pexpect
import chess # python-chess

class Match:
	'''
	The Match class setups a chess match between two specified engines.  The white player
	is randomly chosen.

	deep_engine = Engine(depth=20)
	shallow_engine = Engine(depth=10)
	engines = {
		'shallow': shallow_engine,
		'deep': deep_engine,
		}

	m = Match(engines=engines)

	m.move() advances the game by one move.
	
	m.run() plays the game until completion or 200 moves have been played,
	returning the winning engine name.
	'''
	def __init__(self, engines):
		random_bin = randint(0,1)
		self.white = list(engines.keys())[random_bin]
		self.black = list(engines.keys())[not random_bin]
		self.white_engine = engines.get(self.white)
		self.black_engine = engines.get(self.black)
		self.moves = []
		self.white_engine.new_game()
		self.black_engine.new_game()
		self.winner = None
		self.winner_name = None

	def move(self):
		if len(self.moves)>200:
			return False
		elif len(self.moves) % 2:
			active_engine = self.black_engine
			active_engine_name = self.black
			inactive_engine = self.white_engine
			inactive_engine_name = self.white
		else:
			active_engine = self.white_engine
			active_engine_name = self.white
			inactive_engine = self.black_engine
			inactive_engine_name = self.black
		active_engine.set_position(self.moves)
		move_dict=active_engine.best_move()
		best_move = move_dict.get('move')
		info = move_dict.get('info')
		ponder = move_dict.get('ponder')
		self.moves.append(best_move)
		
		if ponder != '(none)': 
			return True
		else:
			mateloc = info.find('mate')
			if mateloc>=0:
				matenum = int(info[mateloc+5])
				if matenum>0:
					self.winner_engine = active_engine
					self.winner = active_engine_name
				elif matenum<0: 
					self.winner_engine = inactive_engine
					self.winner = inactive_engine_name
			return False

	def run(self):
		'''
		Returns the winning chess engine or "None" if there is a draw.
		'''
		while self.move():
			last_move = self.moves[-1]
			print(last_move)
			#pass
		return self.winner

class Engine(pexpect.spawnu):
	'''
	This initiates the Stockfish chess engine with Ponder set to False.
	'param' allows parameters to be specified by a dictionary object with 'Name' and 'value'
	with value as an integer.

	i.e. the following explicitely sets the default parameters
	{
		"Contempt Factor": 0,
		"Min Split Depth": 0,
		"Threads": 1,
		"Hash": 16,
		"MultiPV": 1,
		"Skill Level": 20,
		"Move Overhead": 30,
		"Minimum Thinking Time": 20,
		"Slow Mover": 80,
	}

	If 'rand' is set to False, any options not explicitely set will be set to the default 
	value.

	-----
	USING RANDOM PARAMETERS
	-----
	If you set 'rand' to True, the 'Contempt' parameter will be set to a random value between
	'rand_min' and 'rand_max' so that you may run automated matches against slightly different
	engines.
	'''
	def __init__(self, depth=10, move_time=100, ponder=False, 
				 param={}, rand=False, rand_min=-10, rand_max=10, prefix=''):
		pexpect.spawnu.__init__(self,'%sstockfish' % prefix, 
								maxread=20000, timeout=300)
		self.readline()
		self.depth = depth
		self.move_time = move_time
		self.ponder = ponder
		self.put('uci')
		self.is_ready()
		if not ponder:
			self.set_option('Ponder', False)

		base_param = {
			"Write Debug Log": "false",
			"Contempt Factor": 0, # There are some stockfish versions with Contempt Factor
			"Contempt": 0,        # and others with Contempt. Just try both.
			"Min Split Depth": 0,
			"Threads": 1,
			"Hash": 16,
			"MultiPV": 1,
			"Skill Level": 20,
			"Move Overhead": 30,
			"Minimum Thinking Time": 20,
			"Slow Mover": 80,
			"UCI_Chess960": "false",
			}

		if rand:
			base_param['Contempt'] = randint(rand_min, rand_max),
			base_param['Contempt Factor'] = randint(rand_min, rand_max),

		base_param.update(param)
		self.param = base_param
		for name,value in list(base_param.items()):
			self.set_option(name,value)
		self.board = chess.Board()

	def new_game(self):
		'''
		Calls 'ucinewgame' - this should be run before a new game
		'''
		self.put('ucinewgame')
		self.is_ready()
		self.board = chess.Board()

	def put(self, command):
		self.sendline(command)
	
	def set_option(self,option_name, value):
		self.put('setoption name %s value %s' % (option_name,str(value)))
		stdout = self.is_ready()
		if stdout.find('No such')>=0:
			print("stockfish was unable to set option %s" % option_name)
		else:
			setattr(self,option_name,value)

	def set_move(self, move):
		cmd = 'position fen %s moves %s' % (self.board.fen(),move)
		self.put(cmd)
		san = self.board.san(chess.Move.from_uci(move))
		self.board.push_san(san)
		self.is_ready()

	def set_position(self, moves=[]):
		'''
		Move list is a list of moves (i.e. ['e2e4', 'e7e5', ...]) each entry as a string.  Moves must be in full algebraic notation.
		'''
		cmd = 'position fen %s moves %s' % (self.board.fen(),
											self._move_list_to_str(moves))
		self.put(cmd)
		for move in moves:
			san = self.board.san(chess.Move.from_uci(move))
			self.board.push_san(san)
		self.is_ready()

	def set_fen_position(self, fen):
		'''
		set position in fen notation.  Input is a FEN string i.e. "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
		'''
		self.put('position fen %s' % fen)
		self.board.set_fen(fen)
		self.is_ready()

	def go(self,restrict=None):
		cmd = 'go depth %d movetime %d' % (self.depth,self.move_time)
		if restrict:
			cmd += ' searchmoves'
			for move in restrict:
				cmd += ' %s' % move
		self.put(cmd)

	def _move_list_to_str(self,moves):
		'''
		Concatenates a list of strings
		'''
		movestr = ''
		for h in moves:
			movestr += h + ' '
		return movestr.strip()

	def best_move(self,restrict=None):
		last_line = ""
		self.go(restrict=restrict)
		while True:
			text = self.readline().strip()
			split_text = text.split(' ')
			if split_text[0]=='bestmove':
				result = {'move': split_text[1],
						  'info': last_line}
				if len(split_text) >= 4:
					result['ponder'] = split_text[3]
				else:
					result['ponder'] = '(none)'
				break
			last_line = text
		return result

	def best_moves(self,restrict=None):
		self.go(restrict=restrict)
		moves = []
		n_lines = self.MultiPV
		done = False
		for i in range(1,n_lines+1):
			while True:
				text = self.readline().strip()
				split_text = text.split(' ')
				if split_text[0] == 'info':
					try:
						depth = int(split_text[split_text.index('depth')+1])
						pv_num = int(split_text[split_text.index('multipv')+1])
					except ValueError:
						continue
					if pv_num == i and depth == self.depth:
						move = split_text[split_text.index('pv')+1]
						moves.append(move)
						break
				elif split_text[0] == 'bestmove':
					done = True
					break
			if done:
				break
		return moves

	def is_ready(self):
		'''
		Used to synchronize the python engine object with the back-end engine.  Sends 'isready' and waits for 'readyok.'
		'''
		self.put('isready')
		lastline = ''
		i = 0
		while True:
			text = self.readline().strip()
			if text == 'readyok':
				break
			lastline = text
		return lastline

class Board:
	def __init__(self,start_position=None):
		if not start_position:
			w = self.white_symbols
			b = self.black_symbols
			first_rank = {'a':w['r'],'b':w['n'],'c':w['b'],'d':w['q'],
						  'e':w['k'],'f':w['b'],'g':w['n'],'h':w['r']}
			last_rank = {'a':b['r'],'b':b['n'],'c':b['b'],'d':b['q'],
						 'e':b['k'],'f':b['b'],'g':b['n'],'h':b['r']}
		self.position = {}
		self.last_move = ''
		for file_ in 'a b c d e f g h'.split():
			for rank in range(1,9):
				square = '%s%d' % (file_,rank)
				if rank == 1:
					piece = first_rank[file_]
				elif rank == 2:
					piece = self.white_symbols['p']
				elif rank == 7:
					piece = self.black_symbols['p']
				elif rank == 8:
					piece = last_rank[file_]
				else:
					piece = self.empty
				self.position[square] = piece

	white_symbols = {'r':u'\u2656','n':u'\u2658','b':u'\u2657',
					 'q':u'\u2655','k':u'\u2654','p':u'\u2659'}
				
	black_symbols = {'r':u'\u265c','n':u'\u265e','b':u'\u265d',
					 'q':u'\u265b','k':u'\u265a','p':u'\u265f'}

	empty = u''#\u266f'

	def move(self,move,notation=None):
		start = move[:2]
		finish = move[2:4]
		piece = self.position[start]		
		self.position[start] = self.empty
		self.position[finish] = piece
		self.last_move = notation if notation is not None else move
		if piece == self.white_symbols['k']:
			if start == 'e1' and finish == 'g1': # White castles kingside
				self.move('h1f1',notation='O-O')
			elif start == 'e1' and finish == 'c1': # White castles queenside
				self.move('a1d1',notation='O-O-O')
		elif piece == self.black_symbols['k']:
			if start == 'e8' and finish == 'g8': # Black castles kingside
				self.move('h8f8',notation='O-O')
			elif start == 'e8' and finish == 'c8': # Black castles queenside
				self.move('a8d8',notation='O-O-O')
		elif piece == self.white_symbols['p']:
			if len(move) >= 5 and move[4] in ['n','b','r','q']: # White promotes
				self.position[finish] = self.white_symbols[move[4]]
			elif False: # White en passant.  
				pass # To do.  
		elif piece == self.black_symbols['p']:
			if len(move) >= 5 and move[4] in ['n','b','r','q']: # Black promotes
				self.position[finish] = self.black_symbols[move[4]]
			elif False: # Black en passant.  
				pass # To do.  

	def __str__(self):
		string = u'   a  b  c  d e  f  g  h  \n'
		for rank in range(8,0,-1):
			string += u'  ' + u'-'*22 + '\n'
			string += u'%d ' % rank
			for file_ in 'a b c d e f g h'.split():
				square = u'%s%d' % (file_,rank)
				string += u'|%s' % self.position[square]
			string += u'| %d\n' % rank
		string += u'  ' + u'-'*22 + '\n'
		string += u'   a  b  c  d e  f  g  h  \n'
		string += self.last_move
		return string

	def html(self):
		tr = '<tr style="vertical-align:bottom;">'
		string = u'<table style="text-align:center; \
								border-spacing:0pt; \
								font-family:\'Arial Unicode MS\'; \
								border-collapse:collapse; \
								border-color: black; \
								border-style: solid; \
								border-width: 0pt 0pt 0pt 0pt">'	
		for rank in range(8,0,-1):
			string += tr
			string += '<td style="vertical-align:middle; \
								  width:12pt">%d</td>' % rank
			for i,file_ in enumerate('a b c d e f g h'.split()):
				square = u'%s%d' % (file_,rank)
				if (i+rank) % 2 == 0:
					string += '<td style="width:28pt; \
									  	  height:28pt; \
									  	  border-collapse:collapse; \
									  	  border-color: black; \
									  	  border-style: solid; \
									  	  border-width: 0pt 0pt 0pt 0pt">\
									  	  <span style="font-size:250%%;">\
									  	  %s</span></td>' % self.position[square]
				else:
					string += '<td style="background:silver;">\
							   <span style="font-size:250%%;">\
							   %s</span></td>' % self.position[square]
			string += '</tr>'
		string += '<tr><td></td>'
		for file_ in 'a b c d e f g h'.split():
			string += '<td style="text-align:center">%s</td>' % file_
		string += '</tr></table>'
		string += self.last_move
		return string
