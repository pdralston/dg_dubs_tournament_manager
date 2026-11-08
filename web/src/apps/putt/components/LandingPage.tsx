import React, { useState } from 'react';
import './LandingPage.css';

interface LandingPageProps {
  onNavigate: (tab: 'players' | 'leaderboard' | 'tournaments' | 'ace-pot') => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState<'introduction' | 'about' | 'rules'>('introduction');

  const introductionText = `DG-Putt is your one stop shop for following the SVDGC putting league. In the Players list you can find yourself and other's stats including the current seasons earnings, match and team history. The tournaments page will show current and past tournament brackets so you can stay on top of where you are playing and when or re-live your past glories. The Leaderboard offers at a glance standings for each of our divisions battling it out for the end of year trophies and bragging rights. Finally, have a gander at the Ace Pot tracker to see how much a dollar could bring you this week!`;

  const aboutText = `Welcome to DG-Putt! This passion project is a python backed React web application created by David Ralston of the Silicon Valley Disc Golf Club. The engineering, hosting, and maintenance of the app is provided at personal cost for the enjoyment of all that come to sling plastic with us at Hapa's Brewery. If you ever find a bug or have an idea for improvements, reach out to me as I am always looking to improve the experience. There are updates planned for the future, including an overhaul of the entire UI, designed by my loving and extra skilled spouse, Anna Ralston. If you are interested in supporting the application and all of the efforts that go into delivering this app, feel free to send a donation to my Paypal. Thank you for attending SVDGC events. I am happy you're here.`;

  const rulesText = {
    registration: `Cost of entry is $6 with an optional ace pot buy in of an additional $1. Registration begins at 5:30 PM on a league night, refer to the events calendar for schedule. At 6:00 PM players are randomly assigned a partner and play begins. These events are CASH ONLY and players must be PRESENT in order to register.

The first time a player registers they will be asked which division they would like to play in. Divisions have no bearing on payouts or which partner they can be drawn with. Divisions only define who a player is competing against in the season long trophy race. Junior Division players must be <18 through the end of the season. Am players that win a divisional trophy must bump up to the pro division.`,

    gameplay: `You and a randomly chosen partner will progress through a double elimination bracket facing opposing teams in a first to 15, win by two, contest where 25 feet separate you and sweet victory.

Players are responsible for keeping up the pace of play and reporting for their matches promptly when called. The bracket is on display and available via mobile devices through DG Putt. Failure to begin a match 5 minutes after the initial call will result in a forfeiture of that match by the team missing a player(s).

Teams begin play by performing a "flip" of a disc where one team flips and the other calls heads or tails. Winner of the flip will decide whether their team shoots first or second for the first round with the losing team going first in each subsequent round.

A player from each team, armed with two putters each, alternate putting at the basket whilst standing behind the shooting line. When each player has thrown their two putts, the round concludes and the scores for that round are added to the running total.

As the group stage and semi-final rounds take place within "circle one", no step, jump, or falling putts are allowed. All throws must be made from behind the shooting line and balance maintained until after the putter has come to a rest.

A single make results in 1 point. Making both of your putts in a single round, "doubling-up" nets your team 3 points.

Play continues with paired opponents alternating rounds until a team has at least 15 points scored and a 2 point advantage over the other team.

At the conclusion of a game, the winning team must notify one of the approved tournament directors or substitutes the final score of the match and which team won. The players are responsible for making sure the scores and winning team are recorded correctly.

The finals round will consist of a twist of the objective in some way including but not limited to an increase in distance, introduction of obstacles, a change in height or a modification of the basket itself.

If the final round twist results in the basket being placed outside of "circle one" (33 feet/11 meters) then step/jump/falling putts will be allowed.`,

    payouts: `Putting league has prizes each night for 1st through 4th places and a rolling ace pot.

4th place - The very next week of play, not including ace pot, is covered. This only applies to the week immediately following the week where 4th place was won.

3rd place - Thirsty Thirds!, provided by Hapa's Brewing Company, the title sponsor of the SVDGC Putting League, a Crowler (that is a Growler in a can) of choice to each player. Soda is available to non-drinkers.

2nd place - $20 each

1st place - $5 of each entry less the $40 paid out to 2nd place.

Ace-pot If a team goes undefeated in a night, the rolling ace pot will be paid out in addition to the first place winnings. At least one player from the Aceing team must have paid into the ace pot for it to be paid out.

In the event that the total pay out pot, not including ace pot, is less than or equal to $60, 2nd place will receive 10 each with 1st place receiving the balance.`,

    points: `Along with the weekly payout, there is a season long competition for being crowned the overall champion of each of our three divisions, Pro, Am and Junior (<18). Points are earned thusly:
• 1 point for attendance
• 1 point for every match your team wins
• 2 points for making it to the final 4
• 3 points for going undefeated for the event`
  };

  return (
    <div className="landing-page">
      <div className="landing-hero">
        <h1>DG-Putt</h1>
        <nav className="landing-nav">
          <button onClick={() => onNavigate('players')}>Players</button>
          <button onClick={() => onNavigate('leaderboard')}>Leaderboard</button>
          <button onClick={() => onNavigate('tournaments')}>Tournaments</button>
          <button onClick={() => onNavigate('ace-pot')}>Ace Pot</button>
        </nav>
      </div>

      <main className="landing-content">
        <div className="tab-container">
          <div className="tab-buttons">
            <button 
              className={activeTab === 'introduction' ? 'active' : ''}
              onClick={() => setActiveTab('introduction')}
            >
              Introduction
            </button>
            <button 
              className={activeTab === 'about' ? 'active' : ''}
              onClick={() => setActiveTab('about')}
            >
              About the App
            </button>
            <button 
              className={activeTab === 'rules' ? 'active' : ''}
              onClick={() => setActiveTab('rules')}
            >
              Rules
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'introduction' && (
              <div className="tab-panel">
                <h2>Introduction</h2>
                <p>{introductionText}</p>
              </div>
            )}

            {activeTab === 'about' && (
              <div className="tab-panel">
                <h2>About the App</h2>
                <p>{aboutText}</p>
                <div className="action-buttons">
                  <a href="mailto:ralstontech+dgputt@gmail.com" className="contact-button">
                    Contact
                  </a>
                  <a href="https://www.paypal.com/paypalme/ralstontech" target="_blank" rel="noopener noreferrer" className="support-button">
                    Support the App
                  </a>
                </div>
              </div>
            )}

            {activeTab === 'rules' && (
              <div className="tab-panel">
                <h2>Rules and Points</h2>
                
                <section>
                  <h3>Registration</h3>
                  <p>{rulesText.registration}</p>
                </section>

                <section>
                  <h3>Rules of Play</h3>
                  <p>{rulesText.gameplay}</p>
                </section>

                <section>
                  <h3>Payouts</h3>
                  <p>{rulesText.payouts}</p>
                </section>

                <section>
                  <h3>League Points</h3>
                  <p>{rulesText.points}</p>
                </section>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default LandingPage;
