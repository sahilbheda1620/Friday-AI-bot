import asyncio
import websockets
import json
import datetime
import re
import webbrowser
import subprocess
import platform
from geminitest import get_ai_response_with_context

class FridayAssistant:
    def __init__(self):
        self.cancel_event = None
        self.current_task = None
        self.connected_clients = set()

    async def handle_client(self, websocket):
        """Handle incoming client connections"""
        self.connected_clients.add(websocket)
        try:
            print(f"New client connected. Total clients: {len(self.connected_clients)}")
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data['type'] == 'command':
                        # Get chat history if provided
                        history = data.get('history', [])
                        await self.process_command(data['text'], websocket, history)
                    elif data['type'] == 'stop':
                        if self.cancel_event:
                            self.cancel_event.set()
                            if self.current_task and not self.current_task.done():
                                self.current_task.cancel()
                            await self.send_response(websocket, "Response stopped")
                except json.JSONDecodeError:
                    await self.send_response(websocket, "Invalid message format")
                except Exception as e:
                    print(f"Error handling message: {e}")
                    await self.send_response(websocket, "An error occurred processing your request")
        except websockets.exceptions.ConnectionClosed:
            print("Client disconnected")
        finally:
            self.connected_clients.discard(websocket)
            print(f"Client removed. Total clients: {len(self.connected_clients)}")

    async def send_response(self, websocket, text):
        """Send response to client"""
        try:
            await websocket.send(json.dumps({"type": "response", "text": text}))
        except Exception as e:
            print(f"Error sending response: {e}")

    async def process_command(self, text, websocket, history=[]):
        """Process user commands"""
        self.cancel_event = asyncio.Event()
        text_lower = text.lower()

        try:
            if "open" in text_lower and not any(word in text_lower for word in ["how", "what", "why", "when", "can you"]):
                await self.handle_open(text, websocket)
            elif "play" in text_lower and not any(word in text_lower for word in ["how", "what", "why", "when", "can you"]):
                await self.handle_play(text, websocket)
            elif any(word in text_lower for word in ["time", "what time", "current time"]):
                await self.handle_time(websocket)
            elif any(word in text_lower for word in ["date", "what date", "today's date"]):
                await self.handle_date(websocket)
            else:
                # Use AI with context for general queries
                await self.handle_ai(text, websocket, history)
        except Exception as e:
            print(f"Error processing command: {e}")
            await self.send_response(websocket, "Sorry, I encountered an error processing your request.")
        finally:
            self.cancel_event = None
            self.current_task = None

    async def handle_open(self, text, websocket):
        """Handle open commands"""
        match = re.search(r"open\s+(.+)", text, re.I)
        if not match:
            await self.send_response(websocket, "Please specify what to open")
            return
        
        target = match.group(1).strip().lower()
        
        apps = {
            "notepad": "notepad" if platform.system() == "Windows" else "nano",
            "calculator": "calc" if platform.system() == "Windows" else "gnome-calculator",
            "chrome": "chrome" if platform.system() == "Windows" else "google-chrome",
            "firefox": "firefox",
            "terminal": "cmd" if platform.system() == "Windows" else "gnome-terminal",
            "cmd": "cmd" if platform.system() == "Windows" else "gnome-terminal",
            "paint": "mspaint" if platform.system() == "Windows" else "gnome-paint",
            "explorer": "explorer" if platform.system() == "Windows" else "nautilus",
        }
        
        if target in apps:
            try:
                if platform.system() == "Windows":
                    subprocess.Popen(apps[target], shell=True)
                else:
                    subprocess.Popen([apps[target]])
                await self.send_response(websocket, f"Opening {target.capitalize()}")
            except Exception as e:
                await self.send_response(websocket, f"Could not open {target}: {str(e)}")
        else:
            try:
                url = target if target.startswith(('http://', 'https://')) else f"https://{target}.com"
                webbrowser.open(url)
                await self.send_response(websocket, f"Opening {target}")
            except Exception as e:
                await self.send_response(websocket, f"Could not open {target}: {str(e)}")

    async def handle_play(self, text, websocket):
        """Handle play music/video commands"""
        try:
            song = text.split("play", 1)[1].strip()
            if not song:
                await self.send_response(websocket, "Please specify what to play")
                return
            
            url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
            webbrowser.open(url)
            await self.send_response(websocket, f"Searching YouTube for: {song}")
        except Exception as e:
            await self.send_response(websocket, f"Error playing content: {str(e)}")

    async def handle_time(self, websocket):
        """Handle time queries"""
        now = datetime.datetime.now().strftime("%I:%M %p")
        await self.send_response(websocket, f"The current time is {now}")

    async def handle_date(self, websocket):
        """Handle date queries"""
        now = datetime.datetime.now().strftime("%A, %B %d, %Y")
        await self.send_response(websocket, f"Today is {now}")

    async def handle_ai(self, text, websocket, history=[]):
        """Handle AI-based responses with context"""
        try:
            self.current_task = asyncio.create_task(
                asyncio.to_thread(get_ai_response_with_context, text, history)
            )
            cancel_task = asyncio.create_task(self.cancel_event.wait())
            
            done, pending = await asyncio.wait(
                [self.current_task, cancel_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
            
            if cancel_task in done:
                return
            
            response = await self.current_task
            await self.send_response(websocket, response)
        except asyncio.CancelledError:
            print("AI task cancelled")
        except Exception as e:
            print(f"AI error: {e}")
            await self.send_response(websocket, "Sorry, I'm having trouble with the AI service right now.")


async def main():
    """Main entry point"""
    assistant = FridayAssistant()
    
    print("=" * 60)
    print("Friday Assistant Backend Starting...")
    print("=" * 60)
    print("Note: AI now has context memory from chat history")
    print("=" * 60)
    
    try:
        async with websockets.serve(
            assistant.handle_client,
            "localhost",
            8765,
            ping_interval=20,
            ping_timeout=10
        ):
            print("Friday is running at ws://localhost:8765")
            print("Waiting for client connections...")
            print("=" * 60)
            print("\nPress Ctrl+C to stop the server\n")
            
            await asyncio.Future()
    except KeyboardInterrupt:
        print("\n\nShutting down Friday Assistant...")
        print("Goodbye!")
    except Exception as e:
        print(f"\nError starting server: {e}")
        print("Make sure port 8765 is not already in use.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass