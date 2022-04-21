import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap } from '@angular/router';
import { ApiComponent } from '../api/api.component';
import { MatchData } from '../model/match-data.model';


@Component({
  selector: 'app-match',
  templateUrl: './match.component.html',
  styleUrls: ['./match.component.scss']
})
export class MatchComponent implements OnInit {

  id: number
  matchData: MatchData
  api: ApiComponent<MatchData>

  constructor(private route: ActivatedRoute, private http: HttpClient) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe((route: ParamMap) => {
      var id = route.get("id");
      if (id) {
        this.id = +id;
      }
    });
    this.api = new ApiComponent(this.http);
    this.api.getCallToURL("http://localhost:8080/match/" + this.id).subscribe((data: any) => {
      this.matchData = data;
      console.log(console.log(this.matchData));
    });
  }
}
